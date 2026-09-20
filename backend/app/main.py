from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from .auth_routes import router as auth_router
from .database import get_db


app = FastAPI(
    title="Pair 4 Handshake API",
    description="Backend API for the Pair 4 Handshake-style application",
    version="1.0.0",
)

app.include_router(auth_router)

@app.get("/")
def root():
    return {
        "message": "Pair 4 Handshake API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.get("/health/db")
def database_health_check(db: Session = Depends(get_db)):
    """
    Confirms that FastAPI can successfully connect to MySQL.
    """
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )