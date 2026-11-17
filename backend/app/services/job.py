"""Job service: student job search and company job postings (publishes job.created)."""

from ..employer_routes import router as employer_job_router
from ..job_routes import router as job_router
from .factory import create_app

app = create_app("job", [job_router, employer_job_router])
