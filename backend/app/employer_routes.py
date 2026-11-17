from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from . import messaging
from .database import get_db, iso_date, log_activity, next_id, today_iso, utcnow, with_id
from .schemas import EmployerJobCreate, EmployerJobResponse, EmployerJobUpdate
from .security import CurrentUser, require_company


router = APIRouter(prefix="/employer", tags=["Employer"])

NOT_YOURS = "Job not found or does not belong to your company."


def _own_job(db: Database, job_id: int, company_id: int) -> dict:
    job = db.jobs.find_one({"_id": job_id, "company_id": company_id})
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_YOURS)
    return job


def _check_salary(salary_min, salary_max) -> None:
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum salary cannot exceed maximum salary.",
        )


@router.post("/jobs", response_model=EmployerJobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    request: EmployerJobCreate,
    current_user: CurrentUser = Depends(require_company),
    db: Database = Depends(get_db),
):
    """
    Creates a job owned by the logged-in company and publishes
    job.created for the search-index worker.
    """

    _check_salary(request.salary_min, request.salary_max)
    company = db.company_profiles.find_one({"_id": current_user.id}, {"company_name": 1}) or {}
    now = utcnow()

    job = {
        "_id": next_id(db, "jobs"),
        "company_id": current_user.id,
        "company_name": company.get("company_name", ""),
        "title": request.title,
        "posted_date": today_iso(),
        "deadline": iso_date(request.deadline),
        "location": request.location,
        "is_remote": request.is_remote,
        "salary_min": request.salary_min,
        "salary_max": request.salary_max,
        "description": request.description,
        "category": request.category,
        "skills": [],
        "created_at": now,
        "updated_at": now,
    }

    db.jobs.insert_one(job)
    log_activity(db, current_user.id, "job_created", {"job_id": job["_id"]})
    messaging.publish(
        messaging.JOB_CREATED,
        key=str(job["_id"]),
        payload={"job_id": job["_id"], "company_id": current_user.id, "title": job["title"]},
    )

    return with_id(job)


@router.get("/jobs", response_model=list[EmployerJobResponse])
def get_my_jobs(current_user: CurrentUser = Depends(require_company), db: Database = Depends(get_db)):
    return [with_id(job) for job in db.jobs.find({"company_id": current_user.id}).sort("created_at", -1)]


@router.get("/jobs/{job_id}", response_model=EmployerJobResponse)
def get_my_job(job_id: int, current_user: CurrentUser = Depends(require_company), db: Database = Depends(get_db)):
    return with_id(_own_job(db, job_id, current_user.id))


@router.put("/jobs/{job_id}", response_model=EmployerJobResponse)
def update_my_job(
    job_id: int,
    request: EmployerJobUpdate,
    current_user: CurrentUser = Depends(require_company),
    db: Database = Depends(get_db),
):
    job = _own_job(db, job_id, current_user.id)
    update_data = request.model_dump(exclude_unset=True)

    _check_salary(
        update_data.get("salary_min", job.get("salary_min")),
        update_data.get("salary_max", job.get("salary_max")),
    )

    if "deadline" in update_data:
        update_data["deadline"] = iso_date(update_data["deadline"])
    update_data["updated_at"] = utcnow()

    db.jobs.update_one({"_id": job_id}, {"$set": update_data})
    return with_id(db.jobs.find_one({"_id": job_id}))


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_job(job_id: int, current_user: CurrentUser = Depends(require_company), db: Database = Depends(get_db)):
    _own_job(db, job_id, current_user.id)

    # MySQL cascaded these deletes; MongoDB needs them spelled out.
    db.jobs.delete_one({"_id": job_id})
    db.applications.delete_many({"job_id": job_id})
    db.saved_items.delete_many({"item_type": "job", "item_id": job_id})
    log_activity(db, current_user.id, "job_deleted", {"job_id": job_id})

    return None
