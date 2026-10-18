from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Event, User
from .schemas import (
    EmployerEventCreate,
    EmployerEventResponse,
    EmployerEventUpdate,
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