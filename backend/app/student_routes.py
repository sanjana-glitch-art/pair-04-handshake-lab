import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pymongo.database import Database

from .database import get_db, iso_date, utcnow
from .schemas import (
    StudentDirectoryItem,
    StudentProfileResponse,
    StudentProfileUpdate,
    StudentPublicProfile,
)
from .security import CurrentUser, get_current_user, require_student
from .uploads import remove_upload, save_profile_picture


router = APIRouter(prefix="/students", tags=["Students"])


def profile_to_response(email: str, profile: dict) -> dict:
    return {
        "user_id": profile["_id"],
        "email": email,
        "full_name": profile.get("full_name"),
        "date_of_birth": profile.get("date_of_birth"),
        "city": profile.get("city"),
        "state": profile.get("state"),
        "country": profile.get("country"),
        "career_objective": profile.get("career_objective"),
        "college": profile.get("college"),
        "degree": profile.get("degree"),
        "major": profile.get("major"),
        "graduation_year": profile.get("graduation_year"),
        "cgpa": profile.get("cgpa"),
        "experience": profile.get("experience"),
        "phone": profile.get("phone"),
        "profile_picture_path": profile.get("profile_picture_path"),
        "skills": sorted(profile.get("skills") or [], key=str.lower),
    }


def directory_item(profile: dict) -> dict:
    return {
        "user_id": profile["_id"],
        "full_name": profile.get("full_name"),
        "college": profile.get("college"),
        "major": profile.get("major"),
        "degree": profile.get("degree"),
        "graduation_year": profile.get("graduation_year"),
        "city": profile.get("city"),
        "profile_picture_path": profile.get("profile_picture_path"),
        "skills": sorted(profile.get("skills") or [], key=str.lower),
    }


def resolve_skills(db: Database, names: list[str]) -> list[str]:
    """
    Cleans a skill list and reuses the existing spelling of a known
    skill, so "python" becomes "Python". New skills are added to the
    shared `skills` collection.
    """

    cleaned, seen = [], set()

    for name in names:
        name = name.strip()
        if not name:
            continue
        if len(name) > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Each skill must be 100 characters or fewer.",
            )
        if name.lower() not in seen:
            seen.add(name.lower())
            cleaned.append(name)

    result = []
    for name in cleaned:
        known = db.skills.find_one({"name_lower": name.lower()})
        if known is None:
            db.skills.update_one(
                {"name_lower": name.lower()},
                {"$setOnInsert": {"skill_name": name, "name_lower": name.lower()}},
                upsert=True,
            )
            result.append(name)
        else:
            result.append(known["skill_name"])

    return result


def get_own_profile(current_user: CurrentUser, db: Database) -> dict:
    profile = db.student_profiles.find_one({"_id": current_user.id})
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    return profile


@router.get("/me", response_model=StudentProfileResponse)
def get_my_profile(current_user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return profile_to_response(current_user.email, get_own_profile(current_user, db))


@router.put("/me", response_model=StudentProfileResponse)
def update_my_profile(
    request: StudentProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    get_own_profile(current_user, db)

    update_data = request.model_dump(exclude_unset=True)
    new_email = update_data.pop("email", None)
    new_skills = update_data.pop("skills", None)
    email = current_user.email

    if new_email is not None:
        email = new_email.lower()
        if db.users.find_one({"email": email, "_id": {"$ne": current_user.id}}, {"_id": 1}):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That email is already in use")
        db.users.update_one({"_id": current_user.id}, {"$set": {"email": email, "updated_at": utcnow()}})

    if "date_of_birth" in update_data:
        update_data["date_of_birth"] = iso_date(update_data["date_of_birth"])

    if new_skills is not None:
        update_data["skills"] = resolve_skills(db, new_skills)

    update_data["updated_at"] = utcnow()
    db.student_profiles.update_one({"_id": current_user.id}, {"$set": update_data})

    return profile_to_response(email, get_own_profile(current_user, db))


@router.post("/me/picture", response_model=StudentProfileResponse)
async def upload_my_picture(
    picture: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_student),
    db: Database = Depends(get_db),
):
    profile = get_own_profile(current_user, db)
    new_path = await save_profile_picture(picture)

    db.student_profiles.update_one(
        {"_id": current_user.id},
        {"$set": {"profile_picture_path": new_path, "updated_at": utcnow()}},
    )
    remove_upload(profile.get("profile_picture_path"))

    return profile_to_response(current_user.email, get_own_profile(current_user, db))


def _contains(value: str) -> dict:
    return {"$regex": re.escape(value), "$options": "i"}


@router.get("", response_model=list[StudentDirectoryItem])
def search_students(
    name: str | None = None,
    college: str | None = None,
    major: str | None = None,
    skill: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Student directory, available to students and companies.
    """

    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    query: dict = {}

    if name:
        query["full_name"] = _contains(name)
    if college:
        query["college"] = _contains(college)
    if major:
        query["major"] = _contains(major)
    if skill:
        query["skills"] = {"$regex": f"^{re.escape(skill.strip())}$", "$options": "i"}

    profiles = db.student_profiles.find(query).sort("full_name", 1).skip(offset).limit(limit)
    return [directory_item(profile) for profile in profiles]


@router.get("/majors", response_model=list[str])
def list_majors(current_user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return sorted(major for major in db.student_profiles.distinct("major") if major)


@router.get("/{student_id}", response_model=StudentPublicProfile)
def get_student_profile(
    student_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    One student's profile for the directory and for companies
    reviewing applicants. Date of birth is never shared.
    """

    profile = db.student_profiles.find_one({"_id": student_id})
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    user = db.users.find_one({"_id": student_id}, {"email": 1})

    return {
        **directory_item(profile),
        "email": user["email"],
        "state": profile.get("state"),
        "country": profile.get("country"),
        "career_objective": profile.get("career_objective"),
        "cgpa": profile.get("cgpa"),
        "experience": profile.get("experience"),
        "phone": profile.get("phone"),
    }
