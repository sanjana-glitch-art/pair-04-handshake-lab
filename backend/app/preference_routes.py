from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .database import get_db
from .models import StudentPreference, User
from .schemas import (
    StudentPreferenceResponse,
    StudentPreferenceUpdate,
)
from .security import get_current_user


router = APIRouter(
    prefix="/preferences",
    tags=["Student Preferences"],
)


@router.get(
    "/me",
    response_model=StudentPreferenceResponse,
)
def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns preferences for the logged-in student.
    """

    preferences = (
        db.query(StudentPreference)
        .filter(
            StudentPreference.student_id == current_user.id
        )
        .first()
    )

    if preferences is None:
        return StudentPreferenceResponse(
            student_id=current_user.id
        )

    return preferences


@router.put(
    "/me",
    response_model=StudentPreferenceResponse,
)
def update_my_preferences(
    preference_data: StudentPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates or updates preferences for the logged-in student.
    """

    preferences = (
        db.query(StudentPreference)
        .filter(
            StudentPreference.student_id == current_user.id
        )
        .first()
    )

    if preferences is None:
        preferences = StudentPreference(
            student_id=current_user.id,
            **preference_data.model_dump(),
        )

        db.add(preferences)

    else:
        updates = preference_data.model_dump(
            exclude_unset=True
        )

        for field, value in updates.items():
            setattr(preferences, field, value)

    db.commit()
    db.refresh(preferences)

    return preferences