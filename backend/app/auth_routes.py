from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import StudentProfile, User
from .schemas import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from .security import (
    create_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db),
):
    """
    Creates a new student account and student profile.
    """

    normalized_email = request.email.lower()

    existing_user = (
        db.query(User)
        .filter(User.email == normalized_email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    new_user = User(
        email=normalized_email,
        password_hash=hash_password(request.password),
        user_role="student",
    )

    db.add(new_user)
    db.flush()

    new_profile = StudentProfile(
        user_id=new_user.id,
        full_name=request.full_name,
        college=request.college,
    )

    db.add(new_profile)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Verifies student credentials and returns a JWT token.
    """

    normalized_email = request.email.lower()

    user = (
        db.query(User)
        .filter(User.email == normalized_email)
        .first()
    )

    if not user or not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(
        user_id=user.id,
        user_role=user.user_role,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
    )