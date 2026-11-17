import re

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from . import messaging
from .database import get_db, next_id, today_iso
from .eligibility import is_student_eligible
from .schemas import EventResponse, RegisteredEventResponse
from .security import CurrentUser, get_current_user, get_optional_user


router = APIRouter(prefix="/events", tags=["Student Events"])


def event_to_response(event: dict, profile: dict | None, registered_ids: set[int]) -> EventResponse:
    """
    Adds is_eligible / is_registered when a student is signed in.
    """

    return EventResponse(
        id=event["_id"],
        event_name=event["event_name"],
        description=event["description"],
        event_date=event["event_date"],
        event_time=event["event_time"],
        location=event["location"],
        eligibility=event.get("eligibility"),
        company_name=event.get("company_name", ""),
        is_eligible=(
            is_student_eligible(event.get("eligibility"), profile.get("major"), profile.get("graduation_year"))
            if profile else None
        ),
        is_registered=(event["_id"] in registered_ids) if profile else None,
    )


def student_context(user: CurrentUser | None, db: Database) -> tuple[dict | None, set[int]]:
    if user is None or user.user_role != "student":
        return None, set()

    profile = db.student_profiles.find_one({"_id": user.id}, {"major": 1, "graduation_year": 1}) or {"_id": user.id}
    registered_ids = {r["event_id"] for r in db.event_registrations.find({"student_id": user.id}, {"event_id": 1})}
    return profile, registered_ids


@router.get("", response_model=list[EventResponse])
def get_events(
    search: str | None = None,
    city: str | None = None,
    current_user: CurrentUser | None = Depends(get_optional_user),
    db: Database = Depends(get_db),
):
    """
    Upcoming events in date order.

    - search: partial match on the event name
    - city: partial match on the event location
    """

    query: dict = {"event_date": {"$gte": today_iso()}}
    if search:
        query["event_name"] = {"$regex": re.escape(search), "$options": "i"}
    if city:
        query["location"] = {"$regex": re.escape(city), "$options": "i"}

    events = db.events.find(query).sort([("event_date", 1), ("event_time", 1)])
    profile, registered_ids = student_context(current_user, db)

    return [event_to_response(event, profile, registered_ids) for event in events]


@router.get("/registered", response_model=list[RegisteredEventResponse])
def get_registered_events(current_user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    registrations = list(db.event_registrations.find({"student_id": current_user.id}))
    events = {e["_id"]: e for e in db.events.find({"_id": {"$in": [r["event_id"] for r in registrations]}})}

    rows = [
        RegisteredEventResponse(
            id=registration["_id"],
            event_id=registration["event_id"],
            event_name=events[registration["event_id"]]["event_name"],
            event_date=events[registration["event_id"]]["event_date"],
            event_time=events[registration["event_id"]]["event_time"],
            location=events[registration["event_id"]]["location"],
            registered_at=registration["registered_at"],
        )
        for registration in registrations
        if registration["event_id"] in events
    ]

    return sorted(rows, key=lambda row: (row.event_date, row.event_time))


@router.get("/{event_id}", response_model=EventResponse)
def get_event_details(
    event_id: int,
    current_user: CurrentUser | None = Depends(get_optional_user),
    db: Database = Depends(get_db),
):
    event = db.events.find_one({"_id": event_id})
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    profile, registered_ids = student_context(current_user, db)
    return event_to_response(event, profile, registered_ids)


@router.post("/{event_id}/register", status_code=status.HTTP_202_ACCEPTED)
def register_for_event(
    event_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Checks eligibility, then publishes event.registration_created. The
    event worker stores the registration.
    """

    if current_user.user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can register for events.")

    event = db.events.find_one({"_id": event_id})
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    if event["event_date"] < today_iso():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This event has already taken place.")

    profile = db.student_profiles.find_one({"_id": current_user.id}, {"major": 1, "graduation_year": 1})
    if profile is None or not is_student_eligible(event.get("eligibility"), profile.get("major"), profile.get("graduation_year")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not eligible for this event. Eligibility: {event.get('eligibility')}",
        )

    if db.event_registrations.find_one({"student_id": current_user.id, "event_id": event_id}, {"_id": 1}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You are already registered for this event.")

    registration_id = next_id(db, "event_registrations")

    try:
        message = messaging.publish(
            messaging.EVENT_REGISTRATION_CREATED,
            key=f"{current_user.id}:{event_id}",
            payload={"registration_id": registration_id, "student_id": current_user.id, "event_id": event_id},
        )
    except messaging.PublishError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is temporarily unavailable. Please try again.",
        )

    return {
        "message": "Successfully registered for the event.",
        "registration_id": registration_id,
        "event_id": event_id,
        "kafka_event_id": message["event_id"],
    }
