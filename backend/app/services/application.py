"""Application service: applying, withdrawing, and company review (publishes application.*)."""

from ..application_routes import router as application_router
from ..employer_application_routes import router as employer_application_router
from .factory import create_app

app = create_app("application", [application_router, employer_application_router])
