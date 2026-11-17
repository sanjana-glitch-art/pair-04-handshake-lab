"""Student service: accounts and sign-in, profiles, preferences, saved items, pictures."""

from ..auth_routes import router as auth_router
from ..preference_routes import router as preference_router
from ..saved_routes import router as saved_router
from ..student_routes import router as student_router
from ..uploads import pictures_router
from .factory import create_app

app = create_app("student", [auth_router, student_router, preference_router, saved_router, pictures_router])
