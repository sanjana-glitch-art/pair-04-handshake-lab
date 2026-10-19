from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from .database import get_db
from .models import Skill, StudentProfile, User
from .schemas import (
    StudentDirectoryItem,
    StudentProfileResponse,
    StudentProfileUpdate,
    StudentPublicProfile,
)
from .security import get_current_user, require_student
from .uploads import remove_upload, save_profile_picture


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
        "skills": [skill.skill_name for skill in profile.skills],
    }


def directory_item(profile: StudentProfile) -> dict:
    return {
        "user_id": profile.user_id,
        "full_name": profile.full_name,
        "college": profile.college,
        "major": profile.major,
        "degree": profile.degree,
        "graduation_year": profile.graduation_year,
        "city": profile.city,
        "profile_picture_path": profile.profile_picture_path,
        "skills": [skill.skill_name for skill in profile.skills],
    }


def resolve_skills(
    db: Session,
    names: list[str],
) -> list[Skill]:
    """
    Turns skill names into Skill rows, creating any that are new.
    Matching is case-insensitive so "python" reuses "Python".
    """

    cleaned = []
    seen = set()

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

    skills = []

    for name in cleaned:
        skill = (
            db.query(Skill)
            .filter(Skill.skill_name == name)
            .first()
        )

        if skill is None:
            skill = Skill(skill_name=name)
            db.add(skill)

        skills.append(skill)

    return skills


def get_own_profile(
    current_user: User,
    db: Session,
) -> StudentProfile:
    profile = db.get(StudentProfile, current_user.id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found",
        )

    return profile


@router.get(
    "/me",
    response_model=StudentProfileResponse,
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_own_profile(current_user, db)

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
    profile = get_own_profile(current_user, db)

    update_data = request.model_dump(
        exclude_unset=True
    )

    new_email = update_data.pop("email", None)
    new_skills = update_data.pop("skills", None)

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

    if new_skills is not None:
        profile.skills = resolve_skills(db, new_skills)

    db.commit()
    db.refresh(current_user)
    db.refresh(profile)

    return profile_to_response(current_user, profile)


@router.post(
    "/me/picture",
    response_model=StudentProfileResponse,
)
async def upload_my_picture(
    picture: UploadFile = File(...),
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """
    Uploads or replaces the student's profile picture (PNG or JPEG).
    """

    profile = get_own_profile(current_user, db)

    new_path = await save_profile_picture(picture)
    old_path = profile.profile_picture_path

    profile.profile_picture_path = new_path
    db.commit()
    db.refresh(profile)

    remove_upload(old_path)

    return profile_to_response(current_user, profile)


@router.get(
    "",
    response_model=list[StudentDirectoryItem],
)
def search_students(
    name: str | None = None,
    college: str | None = None,
    major: str | None = None,
    skill: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Student directory, available to students and companies.

    - name: partial match on full name
    - college: partial match on college
    - major: partial match on major
    - skill: exact skill name (case-insensitive), used by the company
      Students tab to search by skillset
    """

    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    query = (
        db.query(StudentProfile)
        .options(selectinload(StudentProfile.skills))
    )

    if name:
        query = query.filter(StudentProfile.full_name.ilike(f"%{name}%"))

    if college:
        query = query.filter(StudentProfile.college.ilike(f"%{college}%"))

    if major:
        query = query.filter(StudentProfile.major.ilike(f"%{major}%"))

    if skill:
        query = query.filter(
            StudentProfile.skills.any(Skill.skill_name.ilike(skill.strip()))
        )

    profiles = (
        query
        .order_by(StudentProfile.full_name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [directory_item(profile) for profile in profiles]


@router.get(
    "/majors",
    response_model=list[str],
)
def list_majors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Distinct majors, used to fill the directory's major filter.
    """

    rows = (
        db.query(StudentProfile.major)
        .filter(StudentProfile.major.is_not(None))
        .distinct()
        .order_by(StudentProfile.major.asc())
        .all()
    )

    return [major for (major,) in rows]


@router.get(
    "/{student_id}",
    response_model=StudentPublicProfile,
)
def get_student_profile(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    One student's profile for the directory and for companies
    reviewing applicants. Date of birth is never shared.
    """

    profile = db.get(StudentProfile, student_id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    return {
        **directory_item(profile),
        "email": profile.user.email,
        "state": profile.state,
        "country": profile.country,
        "career_objective": profile.career_objective,
        "cgpa": profile.cgpa,
        "experience": profile.experience,
        "phone": profile.phone,
    }
