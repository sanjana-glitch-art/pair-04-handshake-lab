"""
The only place in the application that talks to the model runtime.

Everything else goes through ModelClient.complete(messages, tools), so
swapping Ollama for another backend means writing one new subclass.
"""

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx


@dataclass
class ToolCall:
    """
    One tool request from the model.

    arguments is None when the model's arguments could not be parsed;
    parse_error then says why. The agent loop treats that as a
    malformed-arguments failure instead of crashing.
    """

    name: str
    arguments: dict | None
    raw_arguments: str = ""
    parse_error: str | None = None


@dataclass
class ModelReply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class ModelError(Exception):
    """
    The model runtime could not be reached or returned an error.
    """


class ModelClient(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> ModelReply:
        """
        Sends the full message list and tool schemas, returns either
        text, tool calls, or both.
        """


# Some models write a tool call as text instead of using the native
# tool_calls field, e.g. <tool_call>{"name": ..., "arguments": ...}</tool_call>.
TEXT_TOOL_CALL = re.compile(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", re.S)


def parse_text_tool_calls(content: str) -> list[ToolCall]:
    calls = []

    for match in TEXT_TOOL_CALL.finditer(content or ""):
        raw = match.group(1).strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            calls.append(ToolCall(
                name="(unparseable)",
                arguments=None,
                raw_arguments=raw,
                parse_error=f"tool call is not valid JSON: {error.msg}",
            ))
            continue

        arguments = data.get("arguments", {}) if isinstance(data, dict) else None

        calls.append(ToolCall(
            name=str(data.get("name", "")) if isinstance(data, dict) else "",
            arguments=arguments if isinstance(arguments, dict) else None,
            raw_arguments=json.dumps(arguments),
            parse_error=None if isinstance(arguments, dict) else "arguments must be a JSON object",
        ))

    return calls


class OllamaModelClient(ModelClient):
    """
    ModelClient backed by a local Ollama server's /api/chat endpoint.
    """

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        temperature: float = 0.2,
        seed: int | None = None,
        timeout: float = 300.0,
        think: bool | None = None,
    ):
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self.host = (host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.temperature = temperature
        self.seed = seed if seed is not None else int(os.getenv("SEED", "4"))
        # qwen3 can reason before answering. It is slower but follows the
        # tool-argument rules much more closely (see METRICS.md).
        self.num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "12288"))
        self.think = think if think is not None else os.getenv("OLLAMA_THINK", "true").lower() == "true"
        self._http = httpx.Client(timeout=timeout)

    def complete(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> ModelReply:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "think": self.think,
            "keep_alive": "10m",
            "options": {
                "temperature": self.temperature,
                "seed": self.seed,
                # Ollama defaults to a 4096-token window and silently drops
                # the oldest messages beyond it, which breaks follow-ups.
                "num_ctx": self.num_ctx,
            },
        }

        try:
            response = self._http.post(f"{self.host}/api/chat", json=payload)
        except httpx.HTTPError as error:
            raise ModelError(f"could not reach Ollama at {self.host}: {error}") from error

        if response.status_code != 200:
            # Ollama answers 500 when it cannot parse the model's tool
            # call JSON. Surface that as a malformed call, not a crash.
            body = response.text[:500]
            if "tool" in body.lower() and "pars" in body.lower():
                return ModelReply(
                    content="",
                    tool_calls=[ToolCall(
                        name="(unparseable)",
                        arguments=None,
                        raw_arguments=body,
                        parse_error="the runtime could not parse the tool call JSON",
                    )],
                )
            raise ModelError(f"Ollama returned HTTP {response.status_code}: {body}")

        message = response.json().get("message", {})
        content = message.get("content") or ""
        calls = []

        for raw_call in message.get("tool_calls") or []:
            function = raw_call.get("function", {})
            arguments = function.get("arguments", {})

            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments) if arguments.strip() else {}
                except json.JSONDecodeError as error:
                    calls.append(ToolCall(
                        name=function.get("name", ""),
                        arguments=None,
                        raw_arguments=arguments,
                        parse_error=f"arguments are not valid JSON: {error.msg}",
                    ))
                    continue

            calls.append(ToolCall(
                name=function.get("name", ""),
                arguments=arguments if isinstance(arguments, dict) else None,
                raw_arguments=json.dumps(arguments),
                parse_error=None if isinstance(arguments, dict) else "arguments must be a JSON object",
            ))

        if not calls:
            calls = parse_text_tool_calls(content)
            if calls:
                content = TEXT_TOOL_CALL.sub("", content).strip()

        return ModelReply(content=content, tool_calls=calls)
