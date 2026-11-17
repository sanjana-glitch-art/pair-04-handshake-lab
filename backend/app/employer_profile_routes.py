from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, EmailStr, Field
from pymongo.database import Database

from .database import get_db, utcnow
from .security import CurrentUser, require_company
from .uploads import remove_upload, save_profile_picture


router = APIRouter(prefix="/employer", tags=["Employer Profile"])


class EmployerProfileUpdate(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=30, pattern=r"^[0-9+()\-. ]*$")


class EmployerProfileResponse(EmployerProfileUpdate):
    user_id: int
    profile_picture_path: str | None = None


def get_company_profile(current_user: CurrentUser, db: Database) -> dict:
    profile = db.company_profiles.find_one({"_id": current_user.id})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company profile not found.")
    return {**profile, "user_id": profile["_id"]}


@router.get("/profile", response_model=EmployerProfileResponse)
def get_my_employer_profile(current_user: CurrentUser = Depends(require_company), db: Database = Depends(get_db)):
    return get_company_profile(current_user, db)


@router.put("/profile", response_model=EmployerProfileResponse)
def update_my_employer_profile(
    request: EmployerProfileUpdate,
    current_user: CurrentUser = Depends(require_company),
    db: Database = Depends(get_db),
):
    old = get_company_profile(current_user, db)
    db.company_profiles.update_one(
        {"_id": current_user.id},
        {"$set": {**request.model_dump(), "updated_at": utcnow()}},
    )

    # Jobs and events carry a copy of the company name for fast search.
    if old.get("company_name") != request.company_name:
        db.jobs.update_many({"company_id": current_user.id}, {"$set": {"company_name": request.company_name}})
        db.events.update_many({"company_id": current_user.id}, {"$set": {"company_name": request.company_name}})

    return get_company_profile(current_user, db)


@router.post("/profile/picture", response_model=EmployerProfileResponse)
async def upload_my_employer_picture(
    picture: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_company),
    db: Database = Depends(get_db),
):
    profile = get_company_profile(current_user, db)
    new_path = await save_profile_picture(picture)

    db.company_profiles.update_one(
        {"_id": current_user.id},
        {"$set": {"profile_picture_path": new_path, "updated_at": utcnow()}},
    )
    remove_upload(profile.get("profile_picture_path"))

    return get_company_profile(current_user, db)
