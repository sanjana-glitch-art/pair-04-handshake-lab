"""
MongoDB connection and helpers shared by every service.

Lab 2 moved the platform from MySQL to MongoDB. Documents keep integer
ids in `_id` (allocated from the `counters` collection) so the REST API,
the React app, and the assistant's tools still speak in the same ids as
in Lab 1.
"""

import os
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from gridfs import GridFSBucket
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.database import Database


# backend/app/database.py -> repository root holds the .env file.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

PAIR = int(os.getenv("PAIR", "4"))
DB_PREFIX = os.getenv("DB_PREFIX", f"p{PAIR}")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", f"{DB_PREFIX}_handshake")


def mongo_uri() -> str:
    """
    MONGO_URI wins when set (Kubernetes passes it from a Secret).
    Otherwise it is built from host, port, user, and password.
    """

    if os.getenv("MONGO_URI"):
        return os.environ["MONGO_URI"]

    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27047")
    user = os.getenv("MONGO_USER", "")
    password = os.getenv("MONGO_PASSWORD", "")

    if user:
        return f"mongodb://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/?authSource=admin"

    return f"mongodb://{host}:{port}/"


_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client

    if _client is None:
        _client = MongoClient(
            mongo_uri(),
            serverSelectionTimeoutMS=5000,
            maxPoolSize=int(os.getenv("MONGO_POOL_SIZE", "100")),
            tz_aware=False,
        )

    return _client


def get_database() -> Database:
    return get_client()[MONGO_DATABASE]


def get_db():
    """
    FastAPI dependency. The client keeps its own connection pool, so
    there is nothing to close per request.
    """

    yield get_database()


# ------------------------------------------------------------------ ids

def next_id(db: Database, name: str) -> int:
    """
    Allocates the next integer id for a collection, atomically.
    """

    counter = db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    return int(counter["seq"])


def set_counter(db: Database, name: str, value: int) -> None:
    db.counters.update_one({"_id": name}, {"$set": {"seq": int(value)}}, upsert=True)


# ------------------------------------------------------------ conversions
# Dates are stored as ISO strings ("2026-11-20") and times as "HH:MM:SS",
# so range filters and sorting work as plain string comparisons and the
# documents read naturally in mongosh.

def iso_date(value: date | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def iso_time(value: time | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    return str(value)


def utcnow() -> datetime:
    """
    Naive UTC timestamp (MongoDB stores datetimes in UTC).
    """

    return datetime.now(timezone.utc).replace(tzinfo=None)


def today_iso() -> str:
    return date.today().isoformat()


def with_id(document: dict | None, key: str = "id") -> dict | None:
    """
    Copies `_id` to `id` (or another key) for response models.
    """

    if document is None:
        return None

    out = dict(document)
    out[key] = out.pop("_id")
    return out


def picture_bucket(db: Database | None = None) -> GridFSBucket:
    return GridFSBucket(db if db is not None else get_database(), bucket_name="pictures")


def resume_bucket(db: Database | None = None) -> GridFSBucket:
    return GridFSBucket(db if db is not None else get_database(), bucket_name="resumes")


# ---------------------------------------------------------------- indexes

def ensure_indexes(db: Database | None = None) -> None:
    """
    Idempotent; every service calls it at startup.
    """

    db = db if db is not None else get_database()

    db.users.create_index("email", unique=True)
    db.student_profiles.create_index([("full_name", ASCENDING)])
    db.student_profiles.create_index("skills")
    db.jobs.create_index([("deadline", ASCENDING)])
    db.jobs.create_index([("company_id", ASCENDING), ("created_at", DESCENDING)])
    db.jobs.create_index("skills")
    db.applications.create_index([("student_id", ASCENDING), ("job_id", ASCENDING)], unique=True)
    db.applications.create_index([("job_id", ASCENDING)])
    db.events.create_index([("event_date", ASCENDING), ("event_time", ASCENDING)])
    db.events.create_index([("company_id", ASCENDING)])
    db.event_registrations.create_index([("student_id", ASCENDING), ("event_id", ASCENDING)], unique=True)
    db.saved_items.create_index(
        [("student_id", ASCENDING), ("item_type", ASCENDING), ("item_id", ASCENDING)],
        unique=True,
    )
    # Sessions disappear on their own once expires_at passes.
    db.sessions.create_index("expires_at", expireAfterSeconds=0)
    db.sessions.create_index("user_id")
    db.activity_logs.create_index([("user_id", ASCENDING), ("at", DESCENDING)])
    db.activity_logs.create_index("trace_id")
    db.processed_events.create_index("processed_at")
    db.notifications.create_index([("student_id", ASCENDING), ("created_at", DESCENDING)])
    db.student_memory.create_index([("student_id", ASCENDING), ("date", ASCENDING)])
    db.assistant_sessions.create_index("expires_at", expireAfterSeconds=0)
    db.assistant_sessions.create_index([("student_id", ASCENDING), ("updated_at", DESCENDING)])
    db.traces.create_index("trace_id")
    db.traces.create_index([("started_at", DESCENDING)])
    db.dead_letters.create_index([("topic", ASCENDING), ("failed_at", DESCENDING)])


def log_activity(
    db: Database,
    user_id: int | None,
    action: str,
    details: dict | None = None,
    trace_id: str | None = None,
) -> None:
    """
    Append-only activity log (sign-ins, applications, registrations, ...).
    Never stores passwords or tokens.
    """

    db.activity_logs.insert_one({
        "user_id": user_id,
        "action": action,
        "details": details or {},
        "trace_id": trace_id,
        "at": utcnow(),
    })
