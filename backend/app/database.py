from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os


# Locate the project's root .env file.
# database.py is inside:
# project/backend/app/database.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "p4_handshake")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")


# quote_plus safely handles special characters in passwords.
DATABASE_URL = (
    f"mysql+pymysql://"
    f"{quote_plus(MYSQL_USER)}:"
    f"{quote_plus(MYSQL_PASSWORD)}@"
    f"{MYSQL_HOST}:"
    f"{MYSQL_PORT}/"
    f"{MYSQL_DATABASE}"
)


# Engine manages the connection between FastAPI and MySQL.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# Creates database sessions for individual API requests.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    """
    Provides one database session to an API endpoint.
    The session is always closed after the request finishes.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()