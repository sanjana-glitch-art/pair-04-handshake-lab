"""
Password hashing, JWTs, and server-side sessions.

Passwords are bcrypt hashes. A sign-in creates a document in the
`sessions` collection with an expiry; MongoDB's TTL index deletes it
once it expires. The JWT carries the session id (`sid`), so a token
stops working when its session expires or the user signs out, even if
the JWT itself has not expired yet.
"""

import os
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pymongo.database import Database

from .database import get_db, utcnow


JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "temporary-development-secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("SESSION_TTL_MINUTES", "60"))
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))


@dataclass
class CurrentUser:
    id: int
    email: str
    user_role: str
    session_id: str | None = None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_session(db: Database, user_id: int, user_role: str) -> str:
    """
    Stores a session and returns a JWT that points at it.
    """

    session_id = uuid4().hex
    now = utcnow()
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    db.sessions.insert_one({
        "_id": session_id,
        "user_id": user_id,
        "role": user_role,
        "created_at": now,
        "expires_at": expires_at,
    })

    return jwt.encode(
        {"sub": str(user_id), "role": user_role, "sid": session_id, "exp": expires_at},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def create_access_token(user_id: int, user_role: str, db: Database | None = None) -> str:
    """
    Kept for scripts and tests that only need a token.
    """

    from .database import get_database

    return create_session(db if db is not None else get_database(), user_id, user_role)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def user_from_token(token: str | None, db: Database) -> CurrentUser | None:
    if not token:
        return None

    payload = decode_token(token)
    if not payload or payload.get("sub") is None:
        return None

    user_id = int(payload["sub"])
    session_id = payload.get("sid")

    if session_id is None:
        return None

    session = db.sessions.find_one({"_id": session_id, "user_id": user_id})
    # The TTL monitor runs about once a minute, so check expiry here too.
    if session is None or session["expires_at"] <= utcnow():
        return None

    user = db.users.find_one({"_id": user_id}, {"email": 1, "user_role": 1})
    if user is None:
        return None

    return CurrentUser(id=user_id, email=user["email"], user_role=user["user_role"], session_id=session_id)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db),
) -> CurrentUser:
    user = user_from_token(token, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_student(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access is required.")
    return current_user


def require_company(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.user_role != "company":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company access is required.")
    return current_user


def get_optional_user(
    token: str | None = Depends(optional_oauth2_scheme),
    db: Database = Depends(get_db),
) -> CurrentUser | None:
    """
    Public pages show extra detail (eligibility) when signed in.
    """

    return user_from_token(token, db)
