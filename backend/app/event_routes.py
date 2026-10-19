from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from .database import get_db
from .eligibility import is_student_eligible
from .models import (
    CompanyProfile,
    Event,
    EventRegistration,
    StudentProfile,
    User,
)
from .schemas import (
    EventResponse,
    RegisteredEventResponse,
)
from .security import get_current_user, get_optional_user


router = APIRouter(
    prefix="/events",
    tags=["Student Events"],
)


def event_to_response(
    event: Event,
    company_name: str,
    profile: StudentProfile | None,
    registered_ids: set[int],
) -> EventResponse:
    """
    Adds is_eligible / is_registered when a student is signed in.
    """

    return EventResponse(
        id=event.id,
        event_name=event.event_name,
        description=event.description,
        event_date=event.event_date,
        event_time=event.event_time,
        location=event.location,
        eligibility=event.eligibility,
        company_name=company_name,
        is_eligible=(
            is_student_eligible(
                event.eligibility,
                profile.major,
                profile.graduation_year,
            )
            if profile
            else None
        ),
        is_registered=(event.id in registered_ids) if profile else None,
    )


def student_context(
    user: User | None,
    db: Session,
) -> tuple[StudentProfile | None, set[int]]:
    if user is None or user.user_role != "student":
        return None, set()

    profile = db.get(StudentProfile, user.id)

    registered_ids = {
        event_id
        for (event_id,) in (
            db.query(EventRegistration.event_id)
            .filter(EventRegistration.student_id == user.id)
            .all()
        )
    }

    return profile, registered_ids


@router.get(
    "",
    response_model=list[EventResponse],
)
def get_events(
    search: str | None = None,
    city: str | None = None,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    Returns upcoming events for students in increasing date order.

    - search: partial match on the event name
    - city: partial match on the event location
    """

    query = (
        db.query(
            Event,
            CompanyProfile.company_name,
        )
        .join(
            CompanyProfile,
            Event.company_id == CompanyProfile.user_id,
        )
        .filter(Event.event_date >= date.today())
    )

    if search:
        search_value = f"%{search}%"

        query = query.filter(
            Event.event_name.ilike(search_value)
        )

    if city:
        query = query.filter(
            Event.location.ilike(f"%{city}%")
        )

    rows = (
        query
        .order_by(
            Event.event_date.asc(),
            Event.event_time.asc(),
        )
        .all()
    )

    profile, registered_ids = student_context(current_user, db)

    return [
        event_to_response(event, company_name, profile, registered_ids)
        for event, company_name in rows
    ]


@router.get(
    "/registered",
    response_model=list[RegisteredEventResponse],
)
def get_registered_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns events registered by the logged-in student.
    """

    rows = (
        db.query(
            EventRegistration,
            Event,
        )
        .join(
            Event,
            EventRegistration.event_id == Event.id,
        )
        .filter(
            EventRegistration.student_id == current_user.id
        )
        .order_by(
            Event.event_date.asc(),
            Event.event_time.asc(),
        )
        .all()
    )

    return [
        RegisteredEventResponse(
            id=registration.id,
            event_id=event.id,
            event_name=event.event_name,
            event_date=event.event_date,
            event_time=event.event_time,
            location=event.location,
            registered_at=registration.registered_at,
        )
        for registration, event in rows
    ]


@router.get(
    "/{event_id}",
    response_model=EventResponse,
)
def get_event_details(
    event_id: int,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    Returns one event, with eligibility for the signed-in student.
    """

    row = (
        db.query(Event, CompanyProfile.company_name)
        .join(
            CompanyProfile,
            Event.company_id == CompanyProfile.user_id,
        )
        .filter(Event.id == event_id)
        .first()
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    event, company_name = row
    profile, registered_ids = student_context(current_user, db)

    return event_to_response(event, company_name, profile, registered_ids)


@router.post(
    "/{event_id}/register",
    status_code=status.HTTP_201_CREATED,
)
def register_for_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Registers the logged-in student for an event when eligible.
    """

    if current_user.user_role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can register for events.",
        )

    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    if event.event_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event has already taken place.",
        )

    profile = db.get(StudentProfile, current_user.id)

    if profile is None or not is_student_eligible(
        event.eligibility,
        profile.major,
        profile.graduation_year,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You are not eligible for this event. "
                f"Eligibility: {event.eligibility}"
            ),
        )

    existing_registration = (
        db.query(EventRegistration)
        .filter(
            EventRegistration.student_id == current_user.id,
            EventRegistration.event_id == event_id,
        )
        .first()
    )

    if existing_registration is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already registered for this event.",
        )

    registration = EventRegistration(
        student_id=current_user.id,
        event_id=event_id,
    )

    db.add(registration)
    db.commit()
    db.refresh(registration)

    return {
        "message": "Successfully registered for the event.",
        "registration_id": registration.id,
        "event_id": event_id,
    }
