import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from .database import get_db, today_iso
from .schemas import JobDetailsResponse, JobSearchResult


router = APIRouter(prefix="/jobs", tags=["Student Jobs"])


def _contains(value: str) -> dict:
    return {"$regex": re.escape(value), "$options": "i"}


@router.get("", response_model=list[JobSearchResult])
def search_jobs(
    search: str | None = None,
    category: Literal["full_time", "part_time", "on_campus", "internship"] | None = None,
    city: str | None = None,
    remote: bool | None = None,
    min_salary: float | None = None,
    include_closed: bool = False,
    db: Database = Depends(get_db),
):
    """
    Searches jobs for students.

    - search: job title or company name
    - category: internship, full_time, part_time, or on_campus
    - city: job location
    - remote: true or false
    - min_salary: minimum salary
    - include_closed: also return jobs whose deadline has passed
    """

    query: dict = {}

    if not include_closed:
        query["deadline"] = {"$gte": today_iso()}
    if search:
        query["$or"] = [{"title": _contains(search)}, {"company_name": _contains(search)}]
    if category:
        query["category"] = category
    if city:
        query["location"] = _contains(city)
    if remote is not None:
        query["is_remote"] = remote
    if min_salary is not None:
        query["salary_max"] = {"$gte": min_salary}

    projection = {
        "title": 1, "company_name": 1, "location": 1, "is_remote": 1,
        "salary_min": 1, "salary_max": 1, "category": 1, "deadline": 1,
    }

    return [
        JobSearchResult(
            id=job["_id"],
            title=job["title"],
            company_name=job["company_name"],
            location=job["location"],
            is_remote=job["is_remote"],
            salary_min=job.get("salary_min"),
            salary_max=job.get("salary_max"),
            category=job["category"],
            deadline=job["deadline"],
        )
        for job in db.jobs.find(query, projection).sort([("deadline", 1), ("_id", 1)])
    ]


@router.get("/{job_id}", response_model=JobDetailsResponse)
def get_job_details(job_id: int, db: Database = Depends(get_db)):
    job = db.jobs.find_one({"_id": job_id})

    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    company = db.company_profiles.find_one({"_id": job["company_id"]}) or {}

    return JobDetailsResponse(
        id=job["_id"],
        title=job["title"],
        company_name=company.get("company_name", job.get("company_name")),
        company_location=company.get("location"),
        company_description=company.get("description"),
        contact_email=company.get("contact_email"),
        contact_phone=company.get("contact_phone"),
        posted_date=job["posted_date"],
        deadline=job["deadline"],
        location=job["location"],
        is_remote=job["is_remote"],
        salary_min=job.get("salary_min"),
        salary_max=job.get("salary_max"),
        category=job["category"],
        description=job["description"],
    )
