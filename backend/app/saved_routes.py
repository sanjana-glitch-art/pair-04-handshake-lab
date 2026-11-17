from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from .database import get_db, log_activity, next_id, utcnow
from .security import CurrentUser, require_student


router = APIRouter(prefix="/saved", tags=["Saved Items"])


class SavedItemResponse(BaseModel):
    id: int
    item_type: str
    item_id: int
    title: str
    saved_at: str


class SaveRequest(BaseModel):
    item_type: Literal["job", "event"]
    item_id: int


def item_title(db: Database, item_type: str, item_id: int) -> str | None:
    if item_type == "job":
        job = db.jobs.find_one({"_id": item_id}, {"title": 1})
        return job["title"] if job else None
    event = db.events.find_one({"_id": item_id}, {"event_name": 1})
    return event["event_name"] if event else None


def save_item(db: Database, student_id: int, item_type: str, item_id: int) -> tuple[str, str]:
    """
    Shared by POST /saved and the assistant's save tool.
    Returns (outcome, title): outcome is "saved", "exists", or "missing".
    """

    title = item_title(db, item_type, item_id)
    if title is None:
        return "missing", ""

    try:
        db.saved_items.insert_one({
            "_id": next_id(db, "saved_items"),
            "student_id": student_id,
            "item_type": item_type,
            "item_id": item_id,
            "saved_at": utcnow(),
        })
    except DuplicateKeyError:
        return "exists", title

    log_activity(db, student_id, "saved_item", {"item_type": item_type, "item_id": item_id})
    return "saved", title


@router.get("", response_model=list[SavedItemResponse])
def get_my_saved_items(current_user: CurrentUser = Depends(require_student), db: Database = Depends(get_db)):
    """
    Jobs and events the student saved (usually via the AI assistant).
    """

    results = []
    for item in db.saved_items.find({"student_id": current_user.id}).sort("saved_at", -1):
        title = item_title(db, item["item_type"], item["item_id"]) or f"({item['item_type']} removed)"
        results.append(SavedItemResponse(
            id=item["_id"],
            item_type=item["item_type"],
            item_id=item["item_id"],
            title=title,
            saved_at=item["saved_at"].isoformat(),
        ))
    return results


@router.post("", status_code=status.HTTP_201_CREATED)
def save_job_or_event(
    request: SaveRequest,
    response: Response,
    current_user: CurrentUser = Depends(require_student),
    db: Database = Depends(get_db),
):
    """
    Saves a job or event for the signed-in student. The assistant service
    calls this endpoint (with the student's token) after confirmation.
    """

    outcome, title = save_item(db, current_user.id, request.item_type, request.item_id)

    if outcome == "missing":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No {request.item_type} with id {request.item_id} exists.")
    if outcome == "exists":
        response.status_code = status.HTTP_200_OK

    return {"outcome": outcome, "item_type": request.item_type, "item_id": request.item_id, "title": title}


@router.delete("/{saved_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_saved_item(saved_id: int, current_user: CurrentUser = Depends(require_student), db: Database = Depends(get_db)):
    result = db.saved_items.delete_one({"_id": saved_id, "student_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved item not found.")
