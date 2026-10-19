from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Event, EventRegistration, StudentProfile, User
from .schemas import (
    EmployerEventCreate,
    EmployerEventResponse,
    EmployerEventUpdate,
    EventRegistrantResponse,
)
from .security import require_company


router = APIRouter(
    prefix="/employer",
    tags=["Employer Events"],
)


@router.post(
    "/events",
    response_model=EmployerEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    request: EmployerEventCreate,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Creates an event owned by the logged-in company.
    """

    new_event = Event(
        company_id=current_user.id,
        event_name=request.event_name,
        description=request.description,
        event_date=request.event_date,
        event_time=request.event_time,
        location=request.location,
        eligibility=request.eligibility,
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return new_event


@router.get(
    "/events",
    response_model=list[EmployerEventResponse],
)
def get_my_events(
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Returns only events created by the logged-in company.
    """

    return (
        db.query(Event)
        .filter(Event.company_id == current_user.id)
        .order_by(Event.event_date.asc())
        .all()
    )


@router.get(
    "/events/{event_id}",
    response_model=EmployerEventResponse,
)
def get_my_event(
    event_id: int,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Returns one event only if it belongs to the logged-in company.
    """

    event = (
        db.query(Event)
        .filter(
            Event.id == event_id,
            Event.company_id == current_user.id,
        )
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Event not found or does not belong "
                "to your company."
            ),
        )

    return event


@router.put(
    "/events/{event_id}",
    response_model=EmployerEventResponse,
)
def update_my_event(
    event_id: int,
    request: EmployerEventUpdate,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Updates an event owned by the logged-in company.
    """

    event = (
        db.query(Event)
        .filter(
            Event.id == event_id,
            Event.company_id == current_user.id,
        )
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Event not found or does not belong "
                "to your company."
            ),
        )

    update_data = request.model_dump(
        exclude_unset=True,
    )

    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)

    return event


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_my_event(
    event_id: int,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Deletes an event owned by the logged-in company.
    """

    event = (
        db.query(Event)
        .filter(
            Event.id == event_id,
            Event.company_id == current_user.id,
        )
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Event not found or does not belong "
                "to your company."
            ),
        )

    db.delete(event)
    db.commit()

    return None


@router.get(
    "/events/{event_id}/registrations",
    response_model=list[EventRegistrantResponse],
)
def get_event_registrations(
    event_id: int,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """
    Lists the students registered for one of the company's events.
    """

    event = (
        db.query(Event)
        .filter(
            Event.id == event_id,
            Event.company_id == current_user.id,
        )
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Event not found or does not belong "
                "to your company."
            ),
        )

    rows = (
        db.query(EventRegistration, StudentProfile, User.email)
        .join(
            StudentProfile,
            EventRegistration.student_id == StudentProfile.user_id,
        )
        .join(
            User,
            StudentProfile.user_id == User.id,
        )
        .filter(EventRegistration.event_id == event_id)
        .order_by(EventRegistration.registered_at.asc())
        .all()
    )

    return [
        EventRegistrantResponse(
            registration_id=registration.id,
            student_id=profile.user_id,
            full_name=profile.full_name,
            email=email,
            college=profile.college,
            major=profile.major,
            registered_at=registration.registered_at,
        )
        for registration, profile, email in rows
    ]
