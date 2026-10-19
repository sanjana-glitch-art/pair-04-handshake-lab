from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import date, datetime, time
from typing import Literal

class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    college: str = Field(min_length=2, max_length=200)

class CompanySignupRequest(BaseModel):
    company_name: str = Field(
        min_length=2,
        max_length=200,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    location: str | None = Field(
        default=None,
        max_length=200,
    )

    description: str | None = None

    contact_email: EmailStr | None = None

    contact_phone: str | None = Field(
        default=None,
        max_length=30,
    )

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
    skills: list[str] = []

class StudentProfileUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    date_of_birth: date | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    career_objective: str | None = Field(default=None, max_length=2000)
    college: str | None = Field(default=None, max_length=200)
    degree: str | None = Field(default=None, max_length=150)
    major: str | None = Field(default=None, max_length=150)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    cgpa: float | None = Field(default=None, ge=0, le=4)
    experience: str | None = Field(default=None, max_length=5000)
    phone: str | None = Field(
        default=None,
        max_length=30,
        pattern=r"^[0-9+()\-. ]*$",
    )

    # Replaces the student's whole skill list when provided.
    skills: list[str] | None = Field(default=None, max_length=50)


class StudentDirectoryItem(BaseModel):
    user_id: int
    full_name: str
    college: str | None = None
    major: str | None = None
    degree: str | None = None
    graduation_year: int | None = None
    city: str | None = None
    profile_picture_path: str | None = None
    skills: list[str] = []


class StudentPublicProfile(StudentDirectoryItem):
    email: EmailStr
    state: str | None = None
    country: str | None = None
    career_objective: str | None = None
    cgpa: float | None = None
    experience: str | None = None
    phone: str | None = None


class EventRegistrantResponse(BaseModel):
    registration_id: int
    student_id: int
    full_name: str
    email: EmailStr
    college: str | None = None
    major: str | None = None
    registered_at: datetime

class JobSearchResult(BaseModel):
    id: int
    title: str
    company_name: str
    location: str
    is_remote: bool
    salary_min: float | None = None
    salary_max: float | None = None
    category: str
    deadline: date

class JobDetailsResponse(BaseModel):
    id: int
    title: str
    company_name: str
    company_location: str | None = None
    company_description: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    posted_date: date
    deadline: date
    location: str
    is_remote: bool
    salary_min: float | None = None
    salary_max: float | None = None
    category: str
    description: str

class EmployerJobCreate(BaseModel):
    title: str = Field(
        min_length=2,
        max_length=200,
    )

    deadline: date

    location: str = Field(
        min_length=2,
        max_length=200,
    )

    is_remote: bool = False

    salary_min: float | None = Field(
        default=None,
        ge=0,
    )

    salary_max: float | None = Field(
        default=None,
        ge=0,
    )

    description: str = Field(
        min_length=10,
    )

    category: Literal[
        "full_time",
        "part_time",
        "on_campus",
        "internship",
    ]


class EmployerJobUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    deadline: date | None = None

    location: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    is_remote: bool | None = None

    salary_min: float | None = Field(
        default=None,
        ge=0,
    )

    salary_max: float | None = Field(
        default=None,
        ge=0,
    )

    description: str | None = Field(
        default=None,
        min_length=10,
    )

    category: Literal[
        "full_time",
        "part_time",
        "on_campus",
        "internship",
    ] | None = None


class EmployerJobResponse(BaseModel):
    id: int
    company_id: int
    title: str
    posted_date: date
    deadline: date
    location: str
    is_remote: bool
    salary_min: float | None = None
    salary_max: float | None = None
    description: str
    category: str

class ApplicationListItem(BaseModel):
    id: int
    job_id: int
    job_title: str
    company_name: str
    resume_path: str
    applied_at: datetime
    status: str

class EventResponse(BaseModel):
    id: int
    event_name: str
    description: str
    event_date: date
    event_time: time
    location: str
    eligibility: str | None = None
    company_name: str
    is_eligible: bool | None = None
    is_registered: bool | None = None

class RegisteredEventResponse(BaseModel):
    id: int
    event_id: int
    event_name: str
    event_date: date
    event_time: time
    location: str
    registered_at: datetime

class StudentPreferenceUpdate(BaseModel):
    preferred_city: str | None = None

    preferred_category: Literal[
        "full_time",
        "part_time",
        "on_campus",
        "internship",
    ] | None = None

    minimum_salary: float | None = Field(
        default=None,
        ge=0,
    )

    preferred_work_mode: Literal[
        "remote",
        "onsite",
        "hybrid",
    ] | None = None

    preferred_major: str | None = None

    preferred_event_major: str | None = None


class StudentPreferenceResponse(BaseModel):
    student_id: int
    preferred_city: str | None = None
    preferred_category: str | None = None
    minimum_salary: float | None = None
    preferred_work_mode: str | None = None
    preferred_major: str | None = None
    preferred_event_major: str | None = None

class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class AssistantRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=1000,
    )

    history: list[AssistantMessage] = []

class AssistantResponse(BaseModel):
    answer: str
    trace: list[dict] = []

class EmployerEventCreate(BaseModel):
    event_name: str = Field(
        min_length=2,
        max_length=200,
    )

    description: str = Field(
        min_length=10,
    )

    event_date: date

    event_time: time

    location: str = Field(
        min_length=2,
        max_length=200,
    )

    eligibility: str | None = Field(
        default=None,
        max_length=500,
    )


class EmployerEventUpdate(BaseModel):
    event_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        min_length=10,
    )

    event_date: date | None = None

    event_time: time | None = None

    location: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    eligibility: str | None = Field(
        default=None,
        max_length=500,
    )


class EmployerEventResponse(BaseModel):
    id: int
    company_id: int
    event_name: str
    description: str
    event_date: date
    event_time: time
    location: str
    eligibility: str | None = None


class EmployerApplicationResponse(BaseModel):
    application_id: int
    job_id: int
    job_title: str
    student_id: int
    student_name: str
    student_email: EmailStr
    resume_path: str
    applied_at: datetime
    status: str


class EmployerApplicationStatusUpdate(BaseModel):
    status: Literal[
        "Pending",
        "Reviewed",
        "Declined",
    ]