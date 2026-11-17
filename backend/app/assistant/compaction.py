"""
Context compaction for long assistant conversations.

When a conversation's prompt passes COMPACT_AT_PERCENT of the model's
context window (or the student types /compact), the stored history is
replaced by a structured summary: student preferences, jobs, companies,
events, applications, and the current request. Every job and event id
is kept so follow-ups such as "save the second one" still work.
"""

import os
import re

from .model_client import ModelClient, ModelError, estimate_tokens


WARN_AT_PERCENT = 70
COMPACT_AT_PERCENT = int(os.getenv("COMPACT_AT_PERCENT", "60"))

SUMMARY_PROMPT = """Summarize this career-assistant conversation so it can replace the full history.
Use exactly these headings, each followed by short bullet points:
Student preferences:
Jobs discussed:
Companies:
Events discussed:
Applications and saved items:
Current request:
Rules: keep EVERY job id and event id exactly as written (for example id=134), with title,
company, location, pay, and deadline for jobs, and date and eligibility for events, in the order
they were shown. Record what the student asked last and anything still unanswered.
Do not invent anything. Plain text only.

Conversation:
"""

SUMMARY_MARKER = "[Summary of the earlier conversation]"


def transcript(conversation: list[dict]) -> str:
    lines = []
    for message in conversation:
        role = message.get("role")
        if role == "tool":
            lines.append(f"TOOL {message.get('tool_name')} RESULT:\n{message.get('content', '')}")
        elif message.get("tool_calls"):
            calls = ", ".join(f"{c['function']['name']}({c['function'].get('arguments')})" for c in message["tool_calls"])
            lines.append(f"ASSISTANT called {calls}" + (f"\n{message['content']}" if message.get("content") else ""))
        else:
            lines.append(f"{(role or '').upper()}: {message.get('content', '')}")
    return "\n".join(lines)


def fallback_summary(conversation: list[dict]) -> str:
    """
    Used when the model cannot be reached: keeps every id= line from tool
    results plus the student's messages.
    """

    jobs, events, other = [], [], []
    for message in conversation:
        if message.get("role") != "tool":
            continue
        for line in message.get("content", "").splitlines():
            if not line.startswith("id="):
                continue
            target = events if message.get("tool_name") == "search_events" else jobs
            target.append(line.strip())
        if message.get("tool_name") == "get_student_preferences":
            other.append(message["content"].strip())

    asks = [m["content"] for m in conversation if m.get("role") == "user" and not m["content"].startswith(SUMMARY_MARKER)]

    def bullets(items: list[str], empty: str) -> list[str]:
        return [f"- {item}" for item in items] or [f"- {empty}"]

    return "\n".join([
        "Student preferences:", *bullets(other[-1:], "not looked up"),
        "Jobs discussed:", *bullets(jobs, "none"),
        "Companies:", "- see jobs above",
        "Events discussed:", *bullets(events, "none"),
        "Applications and saved items:", "- see conversation",
        "Current request:", f"- {asks[-1] if asks else 'none'}",
    ])


def compact(conversation: list[dict], client: ModelClient, system_tokens: int = 0) -> dict:
    """
    Replaces `conversation` in place with a summary. Returns token counts
    before and after and the summary text.
    """

    before = system_tokens + estimate_tokens(conversation)
    method = "model"

    try:
        summary = client.complete_text([{"role": "user", "content": SUMMARY_PROMPT + transcript(conversation)}]).strip()
        summary = re.sub(r"<think>.*?</think>", "", summary, flags=re.S).strip()
        if len(summary) < 40:
            raise ModelError("summary too short")
    except Exception:  # noqa: BLE001 - model unavailable: keep the facts anyway
        summary = fallback_summary(conversation)
        method = "fallback"

    # Ids the model must not lose: anything shown in a tool result.
    shown_ids = sorted(set(re.findall(r"id=(\d+)", " ".join(
        m.get("content", "") for m in conversation if m.get("role") == "tool"
    ))), key=int)
    missing = [i for i in shown_ids if f"id={i}" not in summary and f"#{i}" not in summary and f" {i} " not in summary]
    if missing:
        summary += "\nIds shown earlier that are still valid: " + ", ".join(f"id={i}" for i in missing)

    original_messages = len(conversation)
    conversation[:] = [
        {"role": "user", "content": f"{SUMMARY_MARKER}\n{summary}"},
        {"role": "assistant", "content": "Understood. I will continue from this summary."},
    ]
    after = system_tokens + estimate_tokens(conversation)

    return {
        "tokens_before": before,
        "tokens_after": after,
        "messages_before": original_messages,
        "messages_after": len(conversation),
        "method": method,
        "summary": summary,
    }


def usage_report(prompt_tokens: int, completion_tokens: int, context_window: int) -> dict:
    """
    What the UI shows after every turn.
    """

    used = prompt_tokens + completion_tokens
    percent = round(100 * used / context_window, 1) if context_window else 0.0
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": used,
        "context_window": context_window,
        "context_percent": percent,
        "warning": percent > WARN_AT_PERCENT,
    }
