from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .database import get_db
from .models import CompanyProfile, Job
from .schemas import (
    JobDetailsResponse,
    JobSearchResult,
)


router = APIRouter(
    prefix="/jobs",
    tags=["Student Jobs"],
)


@router.get(
    "",
    response_model=list[JobSearchResult],
)
def search_jobs(
    search: str | None = None,
    category: str | None = None,
    city: str | None = None,
    remote: bool | None = None,
    min_salary: float | None = None,
    db: Session = Depends(get_db),
):
    """
    Searches jobs for students.

    Supported filters:
    - search: job title or company name
    - category: internship, full_time, part_time, or on_campus
    - city: job location
    - remote: true or false
    - min_salary: minimum salary
    """

    query = (
        db.query(Job, CompanyProfile.company_name)
        .join(
            CompanyProfile,
            Job.company_id == CompanyProfile.user_id,
        )
    )

    if search:
        search_value = f"%{search}%"

        query = query.filter(
            or_(
                Job.title.ilike(search_value),
                CompanyProfile.company_name.ilike(search_value),
            )
        )

    if category:
        query = query.filter(
            Job.category == category
        )

    if city:
        query = query.filter(
            Job.location.ilike(f"%{city}%")
        )

    if remote is not None:
        query = query.filter(
            Job.is_remote == remote
        )

    if min_salary is not None:
        query = query.filter(
            Job.salary_max >= min_salary
        )

    rows = (
        query
        .order_by(Job.deadline.asc())
        .all()
    )

    return [
        JobSearchResult(
            id=job.id,
            title=job.title,
            company_name=company_name,
            location=job.location,
            is_remote=job.is_remote,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            category=job.category,
            deadline=job.deadline,
        )
        for job, company_name in rows
    ]


@router.get(
    "/{job_id}",
    response_model=JobDetailsResponse,
)
def get_job_details(
    job_id: int,
    db: Session = Depends(get_db),
):
    """
    Returns complete details for one job.
    """

    result = (
        db.query(Job, CompanyProfile)
        .join(
            CompanyProfile,
            Job.company_id == CompanyProfile.user_id,
        )
        .filter(Job.id == job_id)
        .first()
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    job, company = result

    return JobDetailsResponse(
        id=job.id,
        title=job.title,
        company_name=company.company_name,
        company_location=company.location,
        company_description=company.description,
        contact_email=company.contact_email,
        contact_phone=company.contact_phone,
        posted_date=job.posted_date,
        deadline=job.deadline,
        location=job.location,
        is_remote=job.is_remote,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        category=job.category,
        description=job.description,
    )