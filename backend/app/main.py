from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from .auth_routes import router as auth_router
from .database import get_db
from fastapi.middleware.cors import CORSMiddleware
from .student_routes import router as student_router
from .job_routes import router as job_router
from .application_routes import router as application_router
from .event_routes import router as event_router
from .preference_routes import router as preference_router
from .assistant_routes import router as assistant_router
from .employer_routes import router as employer_router
from .employer_event_routes import router as employer_event_router
from .employer_application_routes import router as employer_application_router
from .employer_profile_routes import router as employer_profile_router

app = FastAPI(
    title="Pair 4 Handshake API",
    description="Backend API for the Pair 4 Handshake-style application",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(student_router)
app.include_router(job_router)
app.include_router(application_router)
app.include_router(event_router)
app.include_router(preference_router)
app.include_router(assistant_router)
app.include_router(employer_router)
app.include_router(employer_event_router)
app.include_router(employer_application_router)
app.include_router(employer_profile_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

