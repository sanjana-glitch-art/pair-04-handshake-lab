from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import StudentProfile, User
from .schemas import (
    StudentProfileResponse,
    StudentProfileUpdate,
)
from .security import get_current_user


router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


def profile_to_response(
    user: User,
    profile: StudentProfile,
) -> dict:
    return {
        "user_id": profile.user_id,
        "email": user.email,
        "full_name": profile.full_name,
        "date_of_birth": profile.date_of_birth,
        "city": profile.city,
        "state": profile.state,
        "country": profile.country,
        "career_objective": profile.career_objective,
        "college": profile.college,
        "degree": profile.degree,
        "major": profile.major,
        "graduation_year": profile.graduation_year,
        "cgpa": profile.cgpa,
        "experience": profile.experience,
        "phone": profile.phone,
        "profile_picture_path": profile.profile_picture_path,
    }


@router.get(
    "/me",
    response_model=StudentProfileResponse,
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(StudentProfile, current_user.id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found",
        )

    return profile_to_response(current_user, profile)


@router.put(
    "/me",
    response_model=StudentProfileResponse,
)
def update_my_profile(
    request: StudentProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(StudentProfile, current_user.id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found",
        )

    update_data = request.model_dump(
        exclude_unset=True
    )

    new_email = update_data.pop("email", None)

    if new_email is not None:
        normalized_email = new_email.lower()

        existing_user = (
            db.query(User)
            .filter(
                User.email == normalized_email,
                User.id != current_user.id,
            )
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That email is already in use",
            )

        current_user.email = normalized_email

    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(current_user)
    db.refresh(profile)

    return profile_to_response(current_user, profile)