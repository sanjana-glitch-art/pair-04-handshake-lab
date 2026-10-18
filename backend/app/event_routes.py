from datetime import date
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session
from .database import get_db
from .models import (
    CompanyProfile,
    Event,
    EventRegistration,
    User,
)
from .schemas import (
    EventResponse,
    RegisteredEventResponse,
)
from .security import get_current_user

router = APIRouter(
    prefix="/events",
    tags=["Student Events"],
)


@router.get(
    "",
    response_model=list[EventResponse],
)
def get_events(
    search: str | None = None,
    city: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Returns upcoming events for students.
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

    return [
        EventResponse(
            id=event.id,
            event_name=event.event_name,
            description=event.description,
            event_date=event.event_date,
            event_time=event.event_time,
            location=event.location,
            eligibility=event.eligibility,
            company_name=company_name,
        )
        for event, company_name in rows
    ]


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
    Registers the logged-in student for an event.
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