from pathlib import Path
from uuid import uuid4
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session
from .schemas import ApplicationListItem
from .database import get_db
from .models import Application, Job, User, CompanyProfile
from .security import get_current_user

router = APIRouter(
    prefix="/applications",
    tags=["Student Applications"],
)

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def submit_application(
    job_id: int = Form(...),
    resume: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allows a logged-in student to apply for a job with a PDF resume.
    """

    if current_user.user_role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can apply for jobs.",
        )

    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    existing_application = (
        db.query(Application)
        .filter(
            Application.student_id == current_user.id,
            Application.job_id == job_id,
        )
        .first()
    )

    if existing_application is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied to this job.",
        )

    original_filename = resume.filename or ""

    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resumes are allowed.",
        )

    file_contents = await resume.read()

    if len(file_contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume file must be smaller than 5 MB.",
        )

    if not file_contents.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid PDF.",
        )

    saved_filename = f"{uuid4().hex}.pdf"
    saved_path = UPLOAD_DIR / saved_filename

    saved_path.write_bytes(file_contents)

    application = Application(
        student_id=current_user.id,
        job_id=job_id,
        resume_path=f"uploads/{saved_filename}",
        status="Pending",
    )

    try:
        db.add(application)
        db.commit()
        db.refresh(application)

    except Exception:
        db.rollback()

        if saved_path.exists():
            saved_path.unlink()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save application.",
        )

    return {
        "message": "Application submitted successfully.",
        "application_id": application.id,
        "job_id": application.job_id,
        "status": application.status,
    }

@router.get(
    "/me",
    response_model=list[ApplicationListItem],
)
def get_my_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all applications submitted by the logged-in student.
    """

    applications = (
        db.query(
            Application,
            Job.title,
            CompanyProfile.company_name,
        )
        .join(
            Job,
            Application.job_id == Job.id,
        )
        .join(
            CompanyProfile,
            Job.company_id == CompanyProfile.user_id,
        )
        .filter(
            Application.student_id == current_user.id
        )
        .order_by(
            Application.applied_at.desc()
        )
        .all()
    ) 

    return [
        ApplicationListItem(
            id=application.id,
            job_id=application.job_id,
            job_title=job_title,
            company_name=company_name,
            resume_path=application.resume_path,
            applied_at=application.applied_at,
            status=application.status,
        )
        for application, job_title, company_name in applications
    ]