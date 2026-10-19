"""
Human confirmation gate for tools that change state.

The agent loop calls confirm_action before running any tool listed in
GATED_TOOLS. Read-only tools never come through here.
"""

import json
from collections.abc import Callable


# Tools that change the student's data and need a human "yes".
GATED_TOOLS = {"save_job_or_event"}

# ask(tool_name, arguments) -> True to approve, False to decline.
Asker = Callable[[str, dict], bool]


class ConfirmationRequired(Exception):
    """
    Raised by a non-blocking asker (the web UI) when no decision has
    been made yet. The agent loop pauses and the UI shows Yes / No.
    """

    def __init__(self, tool_name: str, arguments: dict):
        super().__init__(f"{tool_name} needs confirmation")
        self.tool_name = tool_name
        self.arguments = arguments


def describe_action(tool_name: str, arguments: dict) -> str:
    if tool_name == "save_job_or_event":
        return (
            f"Save {arguments.get('item_type', 'item')} "
            f"#{arguments.get('item_id', '?')} to your saved items"
        )

    return f"Run {tool_name} with {json.dumps(arguments)}"


def ask_on_terminal(tool_name: str, arguments: dict) -> bool:
    """
    Default asker for the command-line assistant.
    """

    try:
        answer = input(f"  [confirm] {describe_action(tool_name, arguments)}? [y/N] ")
    except EOFError:
        return False

    return answer.strip().lower() in {"y", "yes"}


def confirm_action(
    tool_name: str,
    arguments: dict,
    auto_approve: bool = False,
    ask: Asker | None = None,
) -> bool:
    """
    Returns True when the action may run.

    auto_approve skips the question (used only by scripted tests that
    say so in their output). Otherwise the student is asked; anything
    other than an explicit yes is a decline.
    """

    if auto_approve:
        print(f"  [confirm] auto-approved {tool_name} {json.dumps(arguments)}")
        return True

    approved = bool((ask or ask_on_terminal)(tool_name, arguments))
    print(f"  [confirm] {tool_name} {'approved' if approved else 'DECLINED'} by student")

    return approved
