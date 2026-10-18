from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Job, User
from .schemas import (
    EmployerJobCreate,
    EmployerJobResponse,
    EmployerJobUpdate,
)
from .security import require_company


router = APIRouter(
    prefix="/employer",
    tags=["Employer"],
)


@router.post(
    "/jobs",
    response_model=EmployerJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    request: EmployerJobCreate,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Creates a job owned by the logged-in company.
    """

    if (
        request.salary_min is not None
        and request.salary_max is not None
        and request.salary_min > request.salary_max
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum salary cannot exceed maximum salary.",
        )

    new_job = Job(
        company_id=current_user.id,
        title=request.title,
        posted_date=date.today(),
        deadline=request.deadline,
        location=request.location,
        is_remote=request.is_remote,
        salary_min=request.salary_min,
        salary_max=request.salary_max,
        description=request.description,
        category=request.category,
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return new_job


@router.get(
    "/jobs",
    response_model=list[EmployerJobResponse],
)
def get_my_jobs(
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Returns only jobs created by the logged-in company.
    """

    return (
        db.query(Job)
        .filter(Job.company_id == current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )


@router.get(
    "/jobs/{job_id}",
    response_model=EmployerJobResponse,
)
def get_my_job(
    job_id: int,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Returns one job only if it belongs to the logged-in company.
    """

    job = (
        db.query(Job)
        .filter(
            Job.id == job_id,
            Job.company_id == current_user.id,
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or does not belong to your company.",
        )

    return job


@router.put(
    "/jobs/{job_id}",
    response_model=EmployerJobResponse,
)
def update_my_job(
    job_id: int,
    request: EmployerJobUpdate,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Updates a job owned by the logged-in company.
    """

    job = (
        db.query(Job)
        .filter(
            Job.id == job_id,
            Job.company_id == current_user.id,
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or does not belong to your company.",
        )

    update_data = request.model_dump(
        exclude_unset=True,
    )

    proposed_min = update_data.get(
        "salary_min",
        job.salary_min,
    )

    proposed_max = update_data.get(
        "salary_max",
        job.salary_max,
    )

    if (
        proposed_min is not None
        and proposed_max is not None
        and proposed_min > proposed_max
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum salary cannot exceed maximum salary.",
        )

    for field, value in update_data.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)

    return job


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_my_job(
    job_id: int,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Deletes a job owned by the logged-in company.
    """

    job = (
        db.query(Job)
        .filter(
            Job.id == job_id,
            Job.company_id == current_user.id,
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or does not belong to your company.",
        )

    db.delete(job)
    db.commit()

    return None