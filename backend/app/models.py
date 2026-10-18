from datetime import date, datetime, time
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class User(Base):
    """
    Represents one row in the users table.

    This table stores login information for both students and companies.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    user_role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    student_profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
    )


class StudentProfile(Base):
    """
    Represents one row in the student_profiles table.

    A student profile belongs to exactly one user account.
    """

    __tablename__ = "student_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    career_objective: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    college: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    degree: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    major: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    graduation_year: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    cgpa: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    experience: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    profile_picture_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    user: Mapped[User] = relationship(
        back_populates="student_profile",
    )

class CompanyProfile(Base):
    """
    Represents one company profile.
    """

    __tablename__ = "company_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    company_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    contact_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    contact_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    profile_picture_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )


class Job(Base):
    """
    Represents one job posting.
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "company_profiles.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    posted_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    deadline: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    location: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    is_remote: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    salary_min: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    salary_max: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

class Application(Base):
    """
    Represents one student's application to one job.

    The actual resume PDF is stored in the backend uploads folder.
    The database stores only the file path.
    """

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "student_profiles.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey(
            "jobs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    resume_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    applied_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="Pending",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

class Event(Base):
    """
    Represents a career event that students can view.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "company_profiles.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    event_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    event_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    event_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    location: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    eligibility: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class EventRegistration(Base):
    """
    Connects students with events.

    One student can register for many events.
    One event can have many students.
    """

    __tablename__ = "event_registrations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "student_profiles.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    event_id: Mapped[int] = mapped_column(
        ForeignKey(
            "events.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    registered_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

class StudentPreference(Base):
    """
    Stores the logged-in student's job and event preferences.
    """

    __tablename__ = "student_preferences"

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "student_profiles.user_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    preferred_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    preferred_category: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    minimum_salary: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    preferred_work_mode: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    preferred_major: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    preferred_event_major: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )