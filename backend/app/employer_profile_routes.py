from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import CompanyProfile, User
from .security import require_company


router = APIRouter(
    prefix="/employer",
    tags=["Employer Profile"],
)


class EmployerProfileUpdate(BaseModel):
    company_name: str
    location: str | None = None
    description: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class EmployerProfileResponse(EmployerProfileUpdate):
    user_id: int
    profile_picture_path: str | None = None

    model_config = ConfigDict(
        from_attributes=True
    )


def get_company_profile(
    current_user: User,
    db: Session,
):
    profile = (
        db.query(CompanyProfile)
        .filter(
            CompanyProfile.user_id == current_user.id
        )
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company profile not found.",
        )

    return profile


@router.get(
    "/profile",
    response_model=EmployerProfileResponse,
)
def get_my_employer_profile(
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    return get_company_profile(current_user, db)


@router.put(
    "/profile",
    response_model=EmployerProfileResponse,
)
def update_my_employer_profile(
    request: EmployerProfileUpdate,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    profile = get_company_profile(current_user, db)

    profile.company_name = request.company_name
    profile.location = request.location
    profile.description = request.description
    profile.contact_email = request.contact_email
    profile.contact_phone = request.contact_phone

    db.commit()
    db.refresh(profile)

    return profile