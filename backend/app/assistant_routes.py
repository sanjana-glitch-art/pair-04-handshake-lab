"""
HTTP endpoints for the AI assistant service.

The agent loop lives in app/assistant/. This module keeps each student's
conversation in MongoDB (`assistant_sessions`, so any replica can serve
the next turn), handles the /memory and /compact commands, reports token
usage, compacts long conversations, and publishes one
assistant.interaction event per request for the memory worker.
"""

import os
import time
from datetime import timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pymongo.database import Database

from . import messaging
from .assistant import AssistantSettings, ToolContext, run_assistant
from .assistant.agent import build_system_prompt
from .assistant.compaction import COMPACT_AT_PERCENT, compact, usage_report
from .assistant.confirm import ConfirmationRequired, describe_action
from .assistant.memory import handle_memory_command, prompt_block
from .assistant.model_client import ModelClient, OllamaModelClient, estimate_tokens
from .database import get_db, utcnow
from .observability import current_trace_id, log_event, record_stage
from .schemas import (
    AssistantConfirmRequest,
    AssistantHistoryResponse,
    AssistantPendingAction,
    AssistantRequest,
    AssistantResponse,
)
from .security import CurrentUser, require_student


router = APIRouter(prefix="/assistant", tags=["AI Assistant"])

SESSION_TTL = timedelta(hours=int(os.getenv("ASSISTANT_SESSION_HOURS", "4")))
MAX_SESSIONS_PER_STUDENT = 20

_client: ModelClient | None = None


def get_model_client() -> ModelClient:
    """
    One shared client (its HTTP connection pool is reused). Tests swap it
    with set_model_client.
    """

    global _client
    if _client is None:
        _client = OllamaModelClient()
    return _client


def set_model_client(client: ModelClient | None) -> None:
    global _client
    _client = client


def _ask_in_browser(tool_name: str, arguments: dict) -> bool:
    """
    The web UI cannot block on input(), so the loop pauses and the UI asks.
    """

    raise ConfirmationRequired(tool_name, arguments)


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    return header[7:] if header.lower().startswith("bearer ") else None


# ---------------------------------------------------------------- sessions

def _load_session(db: Database, student_id: int, conversation_id: str | None) -> dict:
    if conversation_id:
        session = db.assistant_sessions.find_one({"_id": conversation_id, "student_id": student_id})
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found. Start a new chat.")
        return session

    # Keep at most MAX_SESSIONS_PER_STUDENT conversations per student.
    old = list(db.assistant_sessions.find({"student_id": student_id}, {"_id": 1}).sort("updated_at", -1).skip(MAX_SESSIONS_PER_STUDENT - 1))
    if old:
        db.assistant_sessions.delete_many({"_id": {"$in": [s["_id"] for s in old]}})

    now = utcnow()
    session = {
        "_id": uuid4().hex,
        "student_id": student_id,
        "messages": [],
        "pending": None,
        "last_user_message": None,
        "usage": None,
        "compactions": [],
        "created_at": now,
        "updated_at": now,
        "expires_at": now + SESSION_TTL,
    }
    db.assistant_sessions.insert_one(session)
    return session


def _save_session(db: Database, session: dict, **changes) -> None:
    session.update(changes)
    now = utcnow()
    db.assistant_sessions.update_one(
        {"_id": session["_id"]},
        {"$set": {**changes, "messages": session["messages"], "updated_at": now, "expires_at": now + SESSION_TTL}},
    )


# ------------------------------------------------------------------ helpers

def _settings(db: Database, user: CurrentUser) -> AssistantSettings:
    return AssistantSettings(
        ask=_ask_in_browser,
        extra_system=prompt_block(db, user.id),
        own_email=user.email,
    )


def _usage(run, client: ModelClient) -> dict:
    report = usage_report(run.prompt_tokens, run.usage[-1]["completion_tokens"] if run.usage else 0, client.context_window)
    report["model_calls"] = len(run.usage)
    return report


def _publish_interaction(user: CurrentUser, message: str, conversation_id: str) -> None:
    """
    Fire-and-forget: the memory worker learns from the request. A Kafka
    outage must not fail the student's request.
    """

    try:
        messaging.publish(
            messaging.ASSISTANT_INTERACTION,
            key=str(user.id),
            payload={"student_id": user.id, "user_message": message[:500], "conversation_id": conversation_id},
            wait=False,
        )
    except Exception as error:  # noqa: BLE001
        log_event("could not publish assistant.interaction", error=str(error))


def _publish_consolidation(student_id: int) -> None:
    messaging.publish(messaging.MEMORY_CONSOLIDATE, key=str(student_id), payload={"student_id": student_id})


def _response(session: dict, run, client: ModelClient, compaction: dict | None = None) -> AssistantResponse:
    pending = None
    if run.pending:
        pending = AssistantPendingAction(
            tool_name=run.pending["tool_name"],
            arguments=run.pending["arguments"],
            description=describe_action(run.pending["tool_name"], run.pending["arguments"]),
        )

    answer = run.answer or ("This changes your saved items, so I need your OK first." if pending else "")

    return AssistantResponse(
        conversation_id=session["_id"],
        answer=answer,
        status=run.status,
        tool_calls=run.tool_calls,
        tool_call_count=run.tool_call_count,
        pending_action=pending,
        usage=session.get("usage"),
        trace_id=current_trace_id(),
        compaction=compaction,
        elapsed_ms=run.elapsed_ms,
    )


class _CommandRun:
    """
    Shape-compatible stand-in for AssistantRun when a command needs no model.
    """

    def __init__(self, answer: str, status_name: str = "command"):
        self.answer, self.status, self.tool_calls, self.tool_call_count = answer, status_name, [], 0
        self.pending, self.elapsed_ms = None, 0.0


def _run_compaction(db: Database, session: dict, user: CurrentUser, client: ModelClient) -> dict:
    system_tokens = estimate_tokens(build_system_prompt(True, None, prompt_block(db, user.id)))
    started = time.perf_counter()
    result = compact(session["messages"], client, system_tokens=system_tokens)
    record_stage("assistant.compaction", (time.perf_counter() - started) * 1000,
                 tokens_before=result["tokens_before"], tokens_after=result["tokens_after"])

    usage = usage_report(result["tokens_after"], 0, client.context_window)
    usage["model_calls"] = 0
    log_event("conversation compacted", conversation_id=session["_id"],
              tokens_before=result["tokens_before"], tokens_after=result["tokens_after"])
    _save_session(db, session, usage=usage,
                  compactions=session.get("compactions", []) + [{k: v for k, v in result.items() if k != "summary"}])
    return result


# ------------------------------------------------------------------- routes

@router.post("/chat", response_model=AssistantResponse)
def chat_with_assistant(
    request: AssistantRequest,
    http_request: Request,
    current_user: CurrentUser = Depends(require_student),
    db: Database = Depends(get_db),
):
    """
    One student message through the agent loop. Commands:
    /memory ..., /compact.
    """

    started = time.perf_counter()
    session = _load_session(db, current_user.id, request.conversation_id)
    client = get_model_client()
    text = request.message.strip()

    if session["pending"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Answer the pending confirmation first.")

    if text.startswith("/memory"):
        answer = handle_memory_command(db, current_user.id, text, publish=_publish_consolidation)
        return _response(session, _CommandRun(answer), client)

    if text.startswith("/compact"):
        if not session["messages"]:
            return _response(session, _CommandRun("There is nothing to compact yet."), client)
        result = _run_compaction(db, session, current_user, client)
        answer = (
            f"Compacted the conversation: about {result['tokens_before']} -> {result['tokens_after']} tokens "
            f"({result['messages_before']} -> {result['messages_after']} messages).\n\n{result['summary']}"
        )
        return _response(session, _CommandRun(answer, "compacted"), client, compaction={k: v for k, v in result.items() if k != "summary"})

    run = run_assistant(
        request.message,
        session["messages"],
        ctx=ToolContext(db=db, student_id=current_user.id, auth_token=_bearer(http_request), trace_id=current_trace_id()),
        client=client,
        settings=_settings(db, current_user),
    )

    usage = _usage(run, client) if run.usage else session.get("usage")
    _save_session(db, session, pending=run.pending, last_user_message=request.message, usage=usage)

    compaction = None
    if usage and usage["context_percent"] >= COMPACT_AT_PERCENT and not run.pending:
        compaction = {k: v for k, v in _run_compaction(db, session, current_user, client).items() if k != "summary"}

    _publish_interaction(current_user, request.message, session["_id"])
    record_stage("assistant.request", (time.perf_counter() - started) * 1000, ok=run.status in {"final", "confirmation_required"},
                 status=run.status, tool_calls=run.tool_call_count, iterations=run.iterations)

    return _response(session, run, client, compaction)


@router.post("/confirm", response_model=AssistantResponse)
def confirm_pending_action(
    request: AssistantConfirmRequest,
    http_request: Request,
    current_user: CurrentUser = Depends(require_student),
    db: Database = Depends(get_db),
):
    """
    Approves or declines the action the assistant paused on.
    """

    started = time.perf_counter()
    session = _load_session(db, current_user.id, request.conversation_id)
    client = get_model_client()

    if not session["pending"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="There is no action waiting for confirmation.")

    pending = session["pending"]
    _save_session(db, session, pending=None)

    run = run_assistant(
        None,
        session["messages"],
        ctx=ToolContext(db=db, student_id=current_user.id, auth_token=_bearer(http_request), trace_id=current_trace_id()),
        client=client,
        settings=_settings(db, current_user),
        resume={"pending": pending, "approved": request.approved, "user_message": session["last_user_message"]},
    )

    usage = _usage(run, client) if run.usage else session.get("usage")
    _save_session(db, session, pending=run.pending, usage=usage)
    record_stage("assistant.request", (time.perf_counter() - started) * 1000, ok=run.status == "final",
                 status=run.status, approved=request.approved)

    return _response(session, run, client)


@router.get("/conversations/{conversation_id}", response_model=AssistantHistoryResponse)
def get_conversation(
    conversation_id: str,
    current_user: CurrentUser = Depends(require_student),
    db: Database = Depends(get_db),
):
    """
    The stored thread, so the UI can restore it after a reload.
    """

    session = _load_session(db, current_user.id, conversation_id)
    visible = [
        {"role": m["role"], "content": m.get("content", "")}
        for m in session["messages"]
        if m["role"] in {"user", "assistant"} and m.get("content")
    ]
    return AssistantHistoryResponse(conversation_id=conversation_id, messages=visible, usage=session.get("usage"))


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def end_conversation(
    conversation_id: str,
    current_user: CurrentUser = Depends(require_student),
    db: Database = Depends(get_db),
):
    """
    Ends the session: the conversation is discarded (memory layer 3).
    What the assistant learned stays in student_memory.
    """

    db.assistant_sessions.delete_one({"_id": conversation_id, "student_id": current_user.id})
