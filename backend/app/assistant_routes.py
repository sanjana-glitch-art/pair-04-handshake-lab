"""
HTTP endpoints for the AI assistant.

The agent loop itself lives in app/assistant/. This module only keeps
each student's conversation between requests and turns a paused
confirmation into a Yes / No question for the React UI.
"""

import threading
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .assistant import AssistantSettings, ToolContext, run_assistant
from .assistant.confirm import ConfirmationRequired, describe_action
from .database import get_db
from .models import User
from .schemas import (
    AssistantConfirmRequest,
    AssistantPendingAction,
    AssistantRequest,
    AssistantResponse,
)
from .security import require_student


router = APIRouter(
    prefix="/assistant",
    tags=["AI Assistant"],
)


# Conversations are kept in memory per (student, conversation id). That
# is enough for a single-process lab server; a restart clears them.
_conversations: dict[tuple[int, str], dict] = {}
_lock = threading.Lock()
MAX_CONVERSATIONS_PER_STUDENT = 20


def _ask_in_browser(tool_name: str, arguments: dict) -> bool:
    """
    The web UI cannot block on input(), so the first time a gated tool
    is requested the loop pauses and the UI asks the student.
    """

    raise ConfirmationRequired(tool_name, arguments)


def _get_conversation(student_id: int, conversation_id: str | None) -> tuple[str, dict]:
    with _lock:
        if conversation_id and (student_id, conversation_id) in _conversations:
            return conversation_id, _conversations[(student_id, conversation_id)]

        if conversation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found. Start a new chat.",
            )

        mine = [key for key in _conversations if key[0] == student_id]
        for key in mine[: max(0, len(mine) - MAX_CONVERSATIONS_PER_STUDENT + 1)]:
            del _conversations[key]

        new_id = uuid4().hex
        state = {"messages": [], "pending": None, "last_user_message": None}
        _conversations[(student_id, new_id)] = state

        return new_id, state


def _to_response(conversation_id: str, run, state: dict) -> AssistantResponse:
    pending = None

    if run.pending:
        pending = AssistantPendingAction(
            tool_name=run.pending["tool_name"],
            arguments=run.pending["arguments"],
            description=describe_action(run.pending["tool_name"], run.pending["arguments"]),
        )

    answer = run.answer or (
        "This changes your saved items, so I need your OK first." if pending else ""
    )

    return AssistantResponse(
        conversation_id=conversation_id,
        answer=answer,
        status=run.status,
        tool_calls=run.tool_calls,
        tool_call_count=run.tool_call_count,
        pending_action=pending,
    )


@router.post(
    "/chat",
    response_model=AssistantResponse,
)
def chat_with_assistant(
    request: AssistantRequest,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """
    Sends one student message through the hand-built agent loop.
    """

    conversation_id, state = _get_conversation(current_user.id, request.conversation_id)

    if state["pending"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Answer the pending confirmation first.",
        )

    run = run_assistant(
        request.message,
        state["messages"],
        ctx=ToolContext(db=db, student_id=current_user.id),
        settings=AssistantSettings(ask=_ask_in_browser),
    )

    state["pending"] = run.pending
    state["last_user_message"] = request.message

    return _to_response(conversation_id, run, state)


@router.post(
    "/confirm",
    response_model=AssistantResponse,
)
def confirm_pending_action(
    request: AssistantConfirmRequest,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """
    Approves or declines the action the assistant paused on, then lets
    the loop finish the turn.
    """

    conversation_id, state = _get_conversation(current_user.id, request.conversation_id)

    if not state["pending"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is no action waiting for confirmation.",
        )

    pending, state["pending"] = state["pending"], None

    run = run_assistant(
        None,
        state["messages"],
        ctx=ToolContext(db=db, student_id=current_user.id),
        settings=AssistantSettings(ask=_ask_in_browser),
        resume={
            "pending": pending,
            "approved": request.approved,
            "user_message": state["last_user_message"],
        },
    )

    state["pending"] = run.pending

    return _to_response(conversation_id, run, state)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def end_conversation(
    conversation_id: str,
    current_user: User = Depends(require_student),
):
    with _lock:
        _conversations.pop((current_user.id, conversation_id), None)
