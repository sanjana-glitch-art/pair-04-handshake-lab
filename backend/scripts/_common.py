"""
Shared setup for the assistant scripts: import path and student lookup.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


def student_id_for(db, email: str) -> int:
    user = db.query(User).filter(User.email == email.lower()).first()

    if user is None or user.user_role != "student":
        raise SystemExit(f"No student account with email {email}. Run the seed generator first.")

    return user.id


__all__ = ["BACKEND_DIR", "REPO_ROOT", "SessionLocal", "student_id_for"]
