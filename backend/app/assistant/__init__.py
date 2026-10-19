"""
Hand-built AI assistant: model client, tools, confirmation gate, and
the agent loop. See agent.run_assistant for the entry point.
"""

from .agent import AssistantRun, AssistantSettings, run_assistant
from .model_client import ModelClient, OllamaModelClient
from .tools import ToolContext

__all__ = [
    "AssistantRun",
    "AssistantSettings",
    "ModelClient",
    "OllamaModelClient",
    "ToolContext",
    "run_assistant",
]
