from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from .models import Event, Job, SavedItem, User
from .security import require_student


router = APIRouter(
    prefix="/saved",
    tags=["Saved Items"],
)


class SavedItemResponse(BaseModel):
    id: int
    item_type: str
    item_id: int
    title: str
    saved_at: str


@router.get(
    "",
    response_model=list[SavedItemResponse],
)
def get_my_saved_items(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """
    Jobs and events the student saved (usually via the AI assistant).
    """

    items = (
        db.query(SavedItem)
        .filter(SavedItem.student_id == current_user.id)
        .order_by(SavedItem.saved_at.desc())
        .all()
    )

    results = []

    for item in items:
        if item.item_type == "job":
            job = db.get(Job, item.item_id)
            title = job.title if job else "(job removed)"
        else:
            event = db.get(Event, item.item_id)
            title = event.event_name if event else "(event removed)"

        results.append(
            SavedItemResponse(
                id=item.id,
                item_type=item.item_type,
                item_id=item.item_id,
                title=title,
                saved_at=item.saved_at.isoformat(),
            )
        )

    return results
