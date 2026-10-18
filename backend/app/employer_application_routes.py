from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    Application,
    Job,
    StudentProfile,
    User,
)
from .schemas import (
    EmployerApplicationResponse,
    EmployerApplicationStatusUpdate,
)
from .security import require_company


router = APIRouter(
    prefix="/employer",
    tags=["Employer Applications"],
)


@router.get(
    "/applications",
    response_model=list[EmployerApplicationResponse],
)
def get_applications_for_my_jobs(
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Returns applications submitted to jobs owned by
    the logged-in company.
    """

    rows = (
        db.query(
            Application,
            Job.title,
            StudentProfile.full_name,
            User.email,
        )
        .join(
            Job,
            Application.job_id == Job.id,
        )
        .join(
            StudentProfile,
            Application.student_id == StudentProfile.user_id,
        )
        .join(
            User,
            StudentProfile.user_id == User.id,
        )
        .filter(
            Job.company_id == current_user.id,
        )
        .order_by(
            Application.applied_at.desc(),
        )
        .all()
    )

    return [
        EmployerApplicationResponse(
            application_id=application.id,
            job_id=application.job_id,
            job_title=job_title,
            student_id=application.student_id,
            student_name=student_name,
            student_email=student_email,
            resume_path=application.resume_path,
            applied_at=application.applied_at,
            status=application.status,
        )
        for (
            application,
            job_title,
            student_name,
            student_email,
        ) in rows
    ]


@router.get(
    "/applications/{application_id}",
    response_model=EmployerApplicationResponse,
)
def get_one_application(
    application_id: int,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Returns one application only if it belongs to one of
    the company's jobs.
    """

    row = (
        db.query(
            Application,
            Job.title,
            StudentProfile.full_name,
            User.email,
        )
        .join(
            Job,
            Application.job_id == Job.id,
        )
        .join(
            StudentProfile,
            Application.student_id == StudentProfile.user_id,
        )
        .join(
            User,
            StudentProfile.user_id == User.id,
        )
        .filter(
            Application.id == application_id,
            Job.company_id == current_user.id,
        )
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Application not found or it does not belong "
                "to one of your jobs."
            ),
        )

    (
        application,
        job_title,
        student_name,
        student_email,
    ) = row

    return EmployerApplicationResponse(
        application_id=application.id,
        job_id=application.job_id,
        job_title=job_title,
        student_id=application.student_id,
        student_name=student_name,
        student_email=student_email,
        resume_path=application.resume_path,
        applied_at=application.applied_at,
        status=application.status,
    )


@router.patch(
    "/applications/{application_id}/status",
    response_model=EmployerApplicationResponse,
)
def update_application_status(
    application_id: int,
    request: EmployerApplicationStatusUpdate,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Updates an application status only when the application
    belongs to one of the company's jobs.
    """

    application = (
        db.query(Application)
        .join(
            Job,
            Application.job_id == Job.id,
        )
        .filter(
            Application.id == application_id,
            Job.company_id == current_user.id,
        )
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Application not found or it does not belong "
                "to one of your jobs."
            ),
        )

    application.status = request.status

    db.commit()

    return get_one_application(
        application_id=application_id,
        current_user=current_user,
        db=db,
    )