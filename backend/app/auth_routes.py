from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from .database import get_db, log_activity, next_id, utcnow
from .schemas import (
    CompanySignupRequest,
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from .security import (
    CurrentUser,
    create_session,
    get_current_user,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


def _create_user(db: Database, email: str, password: str, role: str) -> dict:
    if db.users.find_one({"email": email}, {"_id": 1}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    now = utcnow()
    user = {
        "_id": next_id(db, "users"),
        "email": email,
        "password_hash": hash_password(password),
        "user_role": role,
        "created_at": now,
        "updated_at": now,
    }

    try:
        db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    return user


def _user_response(user: dict) -> dict:
    return {"id": user["_id"], "email": user["email"], "user_role": user["user_role"]}


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def student_signup(request: SignupRequest, db: Database = Depends(get_db)):
    """
    Creates a student account and student profile.
    """

    user = _create_user(db, request.email.lower(), request.password, "student")
    now = utcnow()

    db.student_profiles.insert_one({
        "_id": user["_id"],
        "full_name": request.full_name,
        "college": request.college,
        "skills": [],
        "created_at": now,
        "updated_at": now,
    })
    log_activity(db, user["_id"], "signup", {"role": "student"})

    return _user_response(user)


@router.post("/company/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def company_signup(request: CompanySignupRequest, db: Database = Depends(get_db)):
    """
    Creates a company account and company profile.
    """

    user = _create_user(db, request.email.lower(), request.password, "company")
    now = utcnow()

    db.company_profiles.insert_one({
        "_id": user["_id"],
        "company_name": request.company_name,
        "location": request.location,
        "description": request.description,
        "contact_email": request.contact_email,
        "contact_phone": request.contact_phone,
        "profile_picture_path": None,
        "created_at": now,
        "updated_at": now,
    })
    log_activity(db, user["_id"], "signup", {"role": "company"})

    return _user_response(user)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Database = Depends(get_db)):
    """
    Signs in a student or company. The JWT carries the role and a
    server-side session id that expires.
    """

    user = db.users.find_one({"email": request.email.lower()})

    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_session(db, user["_id"], user["user_role"])
    log_activity(db, user["_id"], "login")

    return TokenResponse(access_token=token, token_type="bearer")


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_for_swagger(form: OAuth2PasswordRequestForm = Depends(), db: Database = Depends(get_db)):
    """
    Form-encoded login used by the Swagger UI "Authorize" button.
    """

    return login(LoginRequest(email=form.username, password=form.password), db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    """
    Ends the server-side session, so the token stops working at once.
    """

    if current_user.session_id:
        db.sessions.delete_one({"_id": current_user.session_id})
    log_activity(db, current_user.id, "logout")
