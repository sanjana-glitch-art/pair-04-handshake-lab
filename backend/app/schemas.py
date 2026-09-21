from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import date

class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    college: str = Field(min_length=2, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    user_role: str

class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: EmailStr
    full_name: str

    date_of_birth: date | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    career_objective: str | None = None
    college: str | None = None
    degree: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    cgpa: float | None = None
    experience: str | None = None
    phone: str | None = None
    profile_picture_path: str | None = None


class StudentProfileUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    date_of_birth: date | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    career_objective: str | None = None
    college: str | None = None
    degree: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    cgpa: float | None = None
    experience: str | None = None
    phone: str | None = None