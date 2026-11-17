"""
What each Kafka consumer does with one message.

Every handler is idempotent:
- the envelope's event_id is recorded in `processed_events` after the
  database write, and a message whose event_id is already there is
  skipped (redelivery after a crash, or the same event published twice);
- the database writes themselves use unique keys (application id,
  student+job, student+event) so even a message that slips past the
  first check cannot create a duplicate row.

The runner commits the Kafka offset only after the handler returns, so
a worker killed mid-message gets the message again after a restart.
"""

import time

from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from .. import messaging
from ..database import get_database, log_activity, utcnow
from ..observability import log_event


DUPLICATE = "duplicate_skipped"
DONE = "processed"


def _demo_pause(payload: dict) -> None:
    """
    Failure-case demo only: "_demo": {"delay_s": 20} makes the worker
    wait before its database write so it can be killed mid-message.
    """

    delay = (payload.get("_demo") or {}).get("delay_s")
    if delay:
        log_event("demo pause before database write", seconds=delay)
        time.sleep(float(delay))


def _already_processed(db: Database, event_id: str) -> bool:
    return db.processed_events.find_one({"_id": event_id}, {"_id": 1}) is not None


def _mark_processed(db: Database, event_id: str, topic: str) -> None:
    try:
        db.processed_events.insert_one({"_id": event_id, "topic": topic, "processed_at": utcnow()})
    except DuplicateKeyError:
        pass


# ------------------------------------------------------------ applications

def application_created(db: Database, message: dict) -> str:
    payload = message["payload"]
    _demo_pause(payload)

    document = {
        "_id": int(payload["application_id"]),
        "student_id": int(payload["student_id"]),
        "job_id": int(payload["job_id"]),
        "resume_path": payload["resume_path"],
        "status": "Pending",
        "applied_at": utcnow(),
        "updated_at": utcnow(),
        "source_event_id": message["event_id"],
        "trace_id": message.get("trace_id"),
    }

    try:
        db.applications.insert_one(document)
    except DuplicateKeyError:
        # Same application id or same student+job: already stored.
        log_event("application already stored; not inserting a duplicate", application_id=document["_id"])
        return DUPLICATE

    log_activity(db, document["student_id"], "application_created",
                 {"application_id": document["_id"], "job_id": document["job_id"]}, message.get("trace_id"))
    return DONE


def application_updated(db: Database, message: dict) -> str:
    payload = message["payload"]
    _demo_pause(payload)

    result = db.applications.update_one(
        {"_id": int(payload["application_id"]), "student_id": int(payload["student_id"])},
        {"$set": {"status": payload["status"], "updated_at": utcnow()}},
    )

    if result.matched_count == 0:
        raise ValueError(f"application {payload['application_id']} not found for student {payload['student_id']}")

    log_activity(db, int(payload["student_id"]), "application_updated",
                 {"application_id": int(payload["application_id"]), "status": payload["status"]}, message.get("trace_id"))
    return DONE


def application_status_changed(db: Database, message: dict) -> str:
    """
    Notification worker: tells the student their application moved.
    """

    payload = message["payload"]
    _demo_pause(payload)

    db.notifications.update_one(
        {"_id": message["event_id"]},
        {"$setOnInsert": {
            "student_id": int(payload["student_id"]),
            "application_id": int(payload["application_id"]),
            "job_title": payload.get("job_title"),
            "old_status": payload.get("old_status"),
            "new_status": payload["new_status"],
            "text": f"Your application for {payload.get('job_title', 'a job')} is now {payload['new_status']}.",
            "read": False,
            "created_at": utcnow(),
        }},
        upsert=True,
    )
    return DONE


# ------------------------------------------------------------------ events

def registration_created(db: Database, message: dict) -> str:
    payload = message["payload"]
    _demo_pause(payload)

    try:
        db.event_registrations.insert_one({
            "_id": int(payload["registration_id"]),
            "student_id": int(payload["student_id"]),
            "event_id": int(payload["event_id"]),
            "registered_at": utcnow(),
            "source_event_id": message["event_id"],
        })
    except DuplicateKeyError:
        return DUPLICATE

    log_activity(db, int(payload["student_id"]), "event_registered",
                 {"event_id": int(payload["event_id"])}, message.get("trace_id"))
    return DONE


# -------------------------------------------------------------------- jobs

def job_created(db: Database, message: dict) -> str:
    """
    Search-index worker: stores lower-case search terms for the new
    posting and bumps the company's open-job count.
    """

    payload = message["payload"]
    job = db.jobs.find_one({"_id": int(payload["job_id"])})

    if job is None:
        raise ValueError(f"job {payload['job_id']} does not exist")

    terms = sorted({
        word
        for text in [job.get("title", ""), job.get("company_name", ""), job.get("location", "")] + list(job.get("skills") or [])
        for word in text.lower().replace(",", " ").split()
        if len(word) > 1
    })

    db.jobs.update_one({"_id": job["_id"]}, {"$set": {"search_terms": terms, "indexed_at": utcnow()}})
    db.company_profiles.update_one({"_id": job["company_id"]}, {"$inc": {"jobs_indexed": 1}})
    return DONE


# --------------------------------------------------------------- assistant

def assistant_interaction(db: Database, message: dict) -> str:
    from ..assistant.memory import learn_from_interaction

    return learn_from_interaction(db, message)


def memory_consolidate(db: Database, message: dict) -> str:
    from ..assistant.memory import consolidate_memory

    return consolidate_memory(db, message)


HANDLERS = {
    messaging.APPLICATION_CREATED: application_created,
    messaging.APPLICATION_UPDATED: application_updated,
    messaging.APPLICATION_STATUS_CHANGED: application_status_changed,
    messaging.EVENT_REGISTRATION_CREATED: registration_created,
    messaging.JOB_CREATED: job_created,
    messaging.ASSISTANT_INTERACTION: assistant_interaction,
    messaging.MEMORY_CONSOLIDATE: memory_consolidate,
}

# Which topics each worker deployment consumes.
WORKER_TOPICS = {
    "application": [messaging.APPLICATION_CREATED, messaging.APPLICATION_UPDATED],
    "notification": [messaging.APPLICATION_STATUS_CHANGED],
    "event": [messaging.EVENT_REGISTRATION_CREATED],
    "job": [messaging.JOB_CREATED],
    "memory": [messaging.ASSISTANT_INTERACTION, messaging.MEMORY_CONSOLIDATE],
}


def process(db: Database, topic: str, message: dict) -> str:
    """
    Idempotent processing of one decoded envelope.
    """

    event_id = message["event_id"]

    if _already_processed(db, event_id):
        log_event("event already processed; skipping", topic=topic, event_id=event_id)
        return DUPLICATE

    outcome = HANDLERS[topic](db, message)
    _mark_processed(db, event_id, topic)
    return outcome


def handle_inline(topic: str, message: dict) -> str:
    """
    Used when Kafka is disabled (tests): same handler, same database.
    """

    return process(get_database(), topic, message)
