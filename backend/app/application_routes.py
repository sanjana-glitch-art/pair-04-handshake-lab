"""
Student application endpoints.

Submitting or withdrawing an application is asynchronous: the API
validates the request, stores the resume in GridFS, publishes
application.created / application.updated to Kafka, and answers
202 Accepted. The application worker writes the database.
"""

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pymongo.database import Database

from . import messaging
from .database import get_db, next_id, today_iso
from .schemas import ApplicationListItem
from .security import CurrentUser, get_current_user, require_student
from .uploads import remove_upload, store_resume, validate_resume


router = APIRouter(prefix="/applications", tags=["Student Applications"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit_application(
    job_id: int = Form(...),
    resume: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Applies to a job with a PDF resume. The application is queued on
    Kafka (application.created) and stored by the application worker.
    """

    if current_user.user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can apply for jobs.")

    job = db.jobs.find_one({"_id": job_id}, {"deadline": 1, "title": 1})
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job["deadline"] < today_iso():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The application deadline for this job has passed.")
    if db.applications.find_one({"student_id": current_user.id, "job_id": job_id}, {"_id": 1}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already applied to this job.")

    contents = await resume.read()
    validate_resume(resume.filename, contents)
    resume_path = store_resume(contents, resume.filename, current_user.id)
    application_id = next_id(db, "applications")

    try:
        message = messaging.publish(
            messaging.APPLICATION_CREATED,
            # Same key for the same student+job keeps retries on one partition, in order.
            key=f"{current_user.id}:{job_id}",
            payload={
                "application_id": application_id,
                "student_id": current_user.id,
                "job_id": job_id,
                "resume_path": resume_path,
            },
        )
    except messaging.PublishError:
        remove_upload(resume_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Applications are temporarily unavailable. Please try again.",
        )

    return {
        "message": "Application submitted successfully.",
        "application_id": application_id,
        "job_id": job_id,
        "status": "Pending",
        "event_id": message["event_id"],
        "trace_id": message["trace_id"],
    }


@router.post("/{application_id}/withdraw", status_code=status.HTTP_202_ACCEPTED)
def withdraw_application(
    application_id: int,
    current_user: CurrentUser = Depends(require_student),
    db: Database = Depends(get_db),
):
    """
    Withdraws one of the student's own applications (application.updated).
    """

    application = db.applications.find_one({"_id": application_id, "student_id": current_user.id})
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    message = messaging.publish(
        messaging.APPLICATION_UPDATED,
        key=f"{current_user.id}:{application['job_id']}",
        payload={"application_id": application_id, "student_id": current_user.id, "status": "Withdrawn"},
    )

    return {"message": "Withdrawal received.", "application_id": application_id, "event_id": message["event_id"]}


@router.get("/me", response_model=list[ApplicationListItem])
def get_my_applications(
    status_filter: Literal["Pending", "Reviewed", "Declined", "Withdrawn"] | None = Query(default=None, alias="status"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    query = {"student_id": current_user.id}
    if status_filter:
        query["status"] = status_filter

    applications = list(db.applications.find(query).sort("applied_at", -1))
    jobs = {
        job["_id"]: job
        for job in db.jobs.find(
            {"_id": {"$in": [a["job_id"] for a in applications]}},
            {"title": 1, "company_name": 1},
        )
    }

    return [
        ApplicationListItem(
            id=application["_id"],
            job_id=application["job_id"],
            job_title=jobs.get(application["job_id"], {}).get("title", "(job removed)"),
            company_name=jobs.get(application["job_id"], {}).get("company_name", ""),
            resume_path=application["resume_path"],
            applied_at=application["applied_at"],
            status=application["status"],
        )
        for application in applications
    ]


@router.get("/notifications/me")
def get_my_notifications(
    current_user: CurrentUser = Depends(require_student),
    db: Database = Depends(get_db),
):
    """
    Status-change notifications written by the notification worker.
    """

    return [
        {
            "id": note["_id"],
            "application_id": note["application_id"],
            "text": note["text"],
            "new_status": note["new_status"],
            "created_at": note["created_at"],
        }
        for note in db.notifications.find({"student_id": current_user.id}).sort("created_at", -1).limit(50)
    ]
