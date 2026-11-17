"""Company service: company sign-up and the company profile."""

from ..auth_routes import router as auth_router
from ..employer_profile_routes import router as employer_profile_router
from ..uploads import pictures_router
from .factory import create_app

app = create_app("company", [auth_router, employer_profile_router, pictures_router])
