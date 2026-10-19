from pydantic import BaseModel, ConfigDict, EmailStr, Field
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import CompanyProfile, User
from .security import require_company
from .uploads import remove_upload, save_profile_picture


router = APIRouter(
    prefix="/employer",
    tags=["Employer Profile"],
)


class EmployerProfileUpdate(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(
        default=None,
        max_length=30,
        pattern=r"^[0-9+()\-. ]*$",
    )


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


@router.post(
    "/profile/picture",
    response_model=EmployerProfileResponse,
)
async def upload_my_employer_picture(
    picture: UploadFile = File(...),
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Uploads or replaces the company logo / profile picture.
    """

    profile = get_company_profile(current_user, db)

    new_path = await save_profile_picture(picture)
    old_path = profile.profile_picture_path

    profile.profile_picture_path = new_path
    db.commit()
    db.refresh(profile)

    remove_upload(old_path)

    return profile
