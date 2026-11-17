from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pymongo.database import Database

from . import messaging
from .database import get_db, log_activity, utcnow
from .schemas import EmployerApplicationResponse, EmployerApplicationStatusUpdate
from .security import CurrentUser, require_company
from .uploads import read_resume


router = APIRouter(prefix="/employer", tags=["Employer Applications"])

NOT_YOURS = "Application not found or it does not belong to one of your jobs."


def _rows(db: Database, query: dict, company_id: int) -> list[dict]:
    """
    Joins applications with the company's jobs and the students.
    """

    my_jobs = {job["_id"]: job["title"] for job in db.jobs.find({"company_id": company_id}, {"title": 1})}
    query = {**query, "job_id": query.get("job_id", {"$in": list(my_jobs)})}
    if isinstance(query["job_id"], int) and query["job_id"] not in my_jobs:
        return []

    applications = list(db.applications.find(query).sort("applied_at", -1))
    student_ids = list({a["student_id"] for a in applications})
    names = {p["_id"]: p["full_name"] for p in db.student_profiles.find({"_id": {"$in": student_ids}}, {"full_name": 1})}
    emails = {u["_id"]: u["email"] for u in db.users.find({"_id": {"$in": student_ids}}, {"email": 1})}

    return [
        {
            "application_id": a["_id"],
            "job_id": a["job_id"],
            "job_title": my_jobs[a["job_id"]],
            "student_id": a["student_id"],
            "student_name": names.get(a["student_id"], ""),
            "student_email": emails.get(a["student_id"], ""),
            "resume_path": a["resume_path"],
            "applied_at": a["applied_at"],
            "status": a["status"],
        }
        for a in applications
    ]


def _one(db: Database, application_id: int, company_id: int) -> dict:
    application = db.applications.find_one({"_id": application_id}, {"job_id": 1})
    rows = _rows(db, {"_id": application_id, "job_id": application["job_id"]}, company_id) if application else []
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_YOURS)
    return rows[0]


@router.get("/applications", response_model=list[EmployerApplicationResponse])
def get_applications_for_my_jobs(
    job_id: int | None = None,
    status_filter: Literal["Pending", "Reviewed", "Declined", "Withdrawn"] | None = Query(default=None, alias="status"),
    current_user: CurrentUser = Depends(require_company),
    db: Database = Depends(get_db),
):
    query: dict = {}
    if job_id is not None:
        query["job_id"] = job_id
    if status_filter is not None:
        query["status"] = status_filter
    return _rows(db, query, current_user.id)


@router.get("/applications/{application_id}", response_model=EmployerApplicationResponse)
def get_one_application(
    application_id: int,
    current_user: CurrentUser = Depends(require_company),
    db: Database = Depends(get_db),
):
    return _one(db, application_id, current_user.id)


@router.patch("/applications/{application_id}/status", response_model=EmployerApplicationResponse)
def update_application_status(
    application_id: int,
    request: EmployerApplicationStatusUpdate,
    current_user: CurrentUser = Depends(require_company),
    db: Database = Depends(get_db),
):
    """
    Changes the status (owner company only) and publishes
    application.status_changed for the notification worker.
    """

    row = _one(db, application_id, current_user.id)

    db.applications.update_one(
        {"_id": application_id},
        {"$set": {"status": request.status, "updated_at": utcnow()}},
    )
    log_activity(db, current_user.id, "application_status_changed",
                 {"application_id": application_id, "status": request.status})

    if row["status"] != request.status:
        messaging.publish(
            messaging.APPLICATION_STATUS_CHANGED,
            key=f"{row['student_id']}:{row['job_id']}",
            payload={
                "application_id": application_id,
                "student_id": row["student_id"],
                "job_title": row["job_title"],
                "old_status": row["status"],
                "new_status": request.status,
            },
        )

    return _one(db, application_id, current_user.id)


@router.get("/applications/{application_id}/resume")
def preview_application_resume(
    application_id: int,
    current_user: CurrentUser = Depends(require_company),
    db: Database = Depends(get_db),
):
    """
    Streams the applicant's PDF inline. Only the company that owns the
    job can open it.
    """

    row = _one(db, application_id, current_user.id)
    contents = read_resume(row["resume_path"])

    if contents is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume file is missing.")

    return Response(content=contents, media_type="application/pdf", headers={"Content-Disposition": "inline"})
