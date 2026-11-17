"""Event service: event search and registration, company events (publishes event.registration_created)."""

from ..employer_event_routes import router as employer_event_router
from ..event_routes import router as event_router
from .factory import create_app

app = create_app("event", [event_router, employer_event_router])
