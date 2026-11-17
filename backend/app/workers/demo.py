"""
Kafka failure-case demos (Lab 2, Part 2). Run inside a service pod so
it uses the cluster's Kafka and MongoDB:

    kubectl -n p4-handshake exec deploy/p4-application-service -- python -m app.workers.demo duplicate
    kubectl -n p4-handshake exec deploy/p4-application-service -- python -m app.workers.demo slow
    kubectl -n p4-handshake exec deploy/p4-application-service -- python -m app.workers.demo poison
    kubectl -n p4-handshake exec deploy/p4-application-service -- python -m app.workers.demo check <application_id>

scripts/kafka_failure_demos.sh runs all three and kills a worker pod for case 2.
"""

import json
import sys
import time
from uuid import uuid4

from .. import messaging
from ..database import get_database, next_id


def _free_student_job(db, email: str = "noprefs.student@example.edu") -> tuple[int, int]:
    """
    A seeded student and an open job they have not applied to. Each demo
    uses its own student so in-flight messages never collide.
    """

    student = db.users.find_one({"email": email})
    applied = {a["job_id"] for a in db.applications.find({"student_id": student["_id"]}, {"job_id": 1})}
    job = db.jobs.find_one({"_id": {"$nin": list(applied)}, "deadline": {"$gte": time.strftime("%Y-%m-%d")}},
                           sort=[("_id", -1)])
    return student["_id"], job["_id"]


def _application_message(db, delay_s: float | None = None, email: str = "noprefs.student@example.edu") -> tuple[str, dict]:
    student_id, job_id = _free_student_job(db, email)
    payload = {
        "application_id": next_id(db, "applications"),
        "student_id": student_id,
        "job_id": job_id,
        "resume_path": "uploads/seed_resume.pdf",
    }
    if delay_s:
        payload["_demo"] = {"delay_s": delay_s}
    message = messaging.envelope("application.created", payload, trace_id=f"demo-{uuid4().hex[:12]}")
    return f"{student_id}:{job_id}", message


def _count(db, application_id: int, student_id: int, job_id: int) -> str:
    by_id = db.applications.count_documents({"_id": application_id})
    by_pair = db.applications.count_documents({"student_id": student_id, "job_id": job_id})
    return f"applications with _id={application_id}: {by_id}; with student {student_id} + job {job_id}: {by_pair}"


def duplicate() -> None:
    db = get_database()
    key, message = _application_message(db)
    p = message["payload"]
    raw = json.dumps(message).encode()

    print(f"[1a] publishing the SAME event twice: event_id={message['event_id']} key={key} trace_id={message['trace_id']}")
    messaging.publish_raw(messaging.APPLICATION_CREATED, key, raw, message["trace_id"])
    messaging.publish_raw(messaging.APPLICATION_CREATED, key, raw, message["trace_id"])

    # Same student + job, new event_id and new application id: a client retry.
    retry = messaging.envelope("application.created", {**p, "application_id": next_id(db, "applications")},
                               trace_id=message["trace_id"])
    print(f"[1b] publishing a retry with a NEW event_id={retry['event_id']} for the same key={key}")
    messaging.publish_raw(messaging.APPLICATION_CREATED, key, json.dumps(retry).encode(), message["trace_id"])

    time.sleep(6)
    print("[1] result:", _count(db, p["application_id"], p["student_id"], p["job_id"]))
    print("[1] processed_events has the event once:",
          db.processed_events.count_documents({"_id": message["event_id"]}))


def slow() -> None:
    db = get_database()
    key, message = _application_message(db, delay_s=25, email="demo.student@example.edu")
    p = message["payload"]
    messaging.publish_raw(messaging.APPLICATION_CREATED, key, json.dumps(message).encode(), message["trace_id"])
    print(f"[2] published slow event_id={message['event_id']} application_id={p['application_id']} "
          f"student={p['student_id']} job={p['job_id']} trace_id={message['trace_id']}")
    print(f"APPLICATION_ID={p['application_id']} STUDENT_ID={p['student_id']} JOB_ID={p['job_id']}")


def check(application_id: int) -> None:
    db = get_database()
    app = db.applications.find_one({"_id": application_id})
    if app is None:
        print(f"application {application_id}: NOT stored")
        return
    print("[2] result:", _count(db, application_id, app["student_id"], app["job_id"]),
          "| source_event_id", app.get("source_event_id"))


def poison() -> None:
    db = get_database()
    key = "poison:1"
    bad = b'{"event_id": "poison-' + uuid4().hex[:8].encode() + b'", "payload": {"student_id": "not-a-number"'  # truncated JSON
    print(f"[3] publishing a poison message (invalid JSON) with key={key}: {bad.decode()}")
    messaging.publish_raw(messaging.APPLICATION_CREATED, key, bad, "demo-poison")

    # A good message on the SAME key (same partition) right behind it.
    student = db.student_profiles.find_one({"_id": {"$gt": 60}}, sort=[("_id", 1)])
    email = db.users.find_one({"_id": student["_id"]})["email"]
    good_key, good = _application_message(db, email=email)
    good_key = key  # force the same partition as the poison message
    messaging.publish_raw(messaging.APPLICATION_CREATED, good_key, json.dumps(good).encode(), good["trace_id"])
    print(f"[3] published a valid message behind it: application_id={good['payload']['application_id']}")

    time.sleep(12)
    dead = db.dead_letters.find_one({"key": key}, sort=[("failed_at", -1)])
    print("[3] dead_letters:", {k: dead[k] for k in ("topic", "partition", "offset", "attempts", "error")} if dead else None)
    print("[3] valid message after the poison one:",
          _count(db, good["payload"]["application_id"], good["payload"]["student_id"], good["payload"]["job_id"]))


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "duplicate":
        duplicate()
    elif command == "slow":
        slow()
    elif command == "poison":
        poison()
    elif command == "check":
        check(int(sys.argv[2]))
    else:
        sys.exit(__doc__)
