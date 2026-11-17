"""
All six Handshake services in one process.

Used for local development without Docker and by the test suite. The
containers run app.services.<name>:app instead (see services/factory.py).
"""

from .application_routes import router as application_router
from .assistant_routes import router as assistant_router
from .auth_routes import router as auth_router
from .employer_application_routes import router as employer_application_router
from .employer_event_routes import router as employer_event_router
from .employer_profile_routes import router as employer_profile_router
from .employer_routes import router as employer_router
from .event_routes import router as event_router
from .job_routes import router as job_router
from .preference_routes import router as preference_router
from .saved_routes import router as saved_router
from .services.factory import create_app
from .student_routes import router as student_router
from .uploads import pictures_router


app = create_app(
    "all",
    [
        auth_router,
        student_router,
        job_router,
        application_router,
        event_router,
        preference_router,
        assistant_router,
        employer_router,
        employer_event_router,
        employer_application_router,
        employer_profile_router,
        saved_router,
        pictures_router,
    ],
    description="Backend API for the Pair 4 Handshake-style application (all services in one process)",
)
