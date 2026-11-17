from fastapi import APIRouter, Depends
from pymongo import ReturnDocument
from pymongo.database import Database

from .database import get_db, utcnow
from .schemas import StudentPreferenceResponse, StudentPreferenceUpdate
from .security import CurrentUser, get_current_user


router = APIRouter(prefix="/preferences", tags=["Student Preferences"])


def _response(student_id: int, document: dict | None) -> dict:
    document = dict(document or {})
    document.pop("_id", None)
    document.pop("updated_at", None)
    return {"student_id": student_id, **document}


@router.get("/me", response_model=StudentPreferenceResponse)
def get_my_preferences(current_user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return _response(current_user.id, db.student_preferences.find_one({"_id": current_user.id}))


@router.put("/me", response_model=StudentPreferenceResponse)
def update_my_preferences(
    preference_data: StudentPreferenceUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Creates or updates preferences for the logged-in student. A first
    save stores every field; later saves change only the fields sent.
    """

    exists = db.student_preferences.find_one({"_id": current_user.id}, {"_id": 1}) is not None
    updates = preference_data.model_dump(exclude_unset=exists)
    updates["updated_at"] = utcnow()

    document = db.student_preferences.find_one_and_update(
        {"_id": current_user.id},
        {"$set": updates},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    return _response(current_user.id, document)
