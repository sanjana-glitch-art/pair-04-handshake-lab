"""
Shared setup for the assistant scripts: import path and student lookup.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import get_database  # noqa: E402


class _Session:
    """
    Lab 2: MongoDB has no per-request session. This wrapper keeps the
    Lab 1 scripts' SessionLocal() / close() shape and forwards
    everything else (db.jobs, db.saved_items, ...) to the database.
    """

    def __init__(self):
        self._db = get_database()

    def __getattr__(self, name):
        return getattr(self._db, name)

    def __getitem__(self, name):
        return self._db[name]

    def close(self):
        pass


def SessionLocal():  # noqa: N802 - keeps the Lab 1 name
    return _Session()


def student_id_for(db, email: str) -> int:
    user = db.users.find_one({"email": email.lower()})

    if user is None or user["user_role"] != "student":
        raise SystemExit(f"No student account with email {email}. Run the seed generator first.")

    return user["_id"]


__all__ = ["BACKEND_DIR", "REPO_ROOT", "SessionLocal", "student_id_for"]
