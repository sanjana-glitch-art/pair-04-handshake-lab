"""AI Assistant service: the hand-built agent loop, memory, and compaction."""

from ..assistant_routes import router as assistant_router
from .factory import create_app

app = create_app("assistant", [assistant_router])
