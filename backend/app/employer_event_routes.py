from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from .database import get_db, iso_date, iso_time, log_activity, next_id, utcnow, with_id
from .schemas import (
    EmployerEventCreate,
    EmployerEventResponse,
    EmployerEventUpdate,
    EventRegistrantResponse,
)
from .security import CurrentUser, require_company


router = APIRouter(prefix="/employer", tags=["Employer Events"])

NOT_YOURS = "Event not found or does not belong to your company."


def _own_event(db: Database, event_id: int, company_id: int) -> dict:
    event = db.events.find_one({"_id": event_id, "company_id": company_id})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_YOURS)
    return event


@router.post("/events", response_model=EmployerEventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    request: EmployerEventCreate,
    current_user: CurrentUser = Depends(require_company),
    db: Database = Depends(get_db),
):
    company = db.company_profiles.find_one({"_id": current_user.id}, {"company_name": 1}) or {}

    event = {
        "_id": next_id(db, "events"),
        "company_id": current_user.id,
        "company_name": company.get("company_name", ""),
        "event_name": request.event_name,
        "description": request.description,
        "event_date": iso_date(request.event_date),
        "event_time": iso_time(request.event_time),
        "location": request.location,
        "eligibility": request.eligibility,
        "created_at": utcnow(),
    }

    db.events.insert_one(event)
    log_activity(db, current_user.id, "event_created", {"event_id": event["_id"]})
    return with_id(event)


@router.get("/events", response_model=list[EmployerEventResponse])
def get_my_events(current_user: CurrentUser = Depends(require_company), db: Database = Depends(get_db)):
    return [with_id(e) for e in db.events.find({"company_id": current_user.id}).sort("event_date", 1)]


@router.get("/events/{event_id}", response_model=EmployerEventResponse)
def get_my_event(event_id: int, current_user: CurrentUser = Depends(require_company), db: Database = Depends(get_db)):
    return with_id(_own_event(db, event_id, current_user.id))


@router.put("/events/{event_id}", response_model=EmployerEventResponse)
def update_my_event(
    event_id: int,
    request: EmployerEventUpdate,
    current_user: CurrentUser = Depends(require_company),
    db: Database = Depends(get_db),
):
    _own_event(db, event_id, current_user.id)
    update_data = request.model_dump(exclude_unset=True)

    if "event_date" in update_data:
        update_data["event_date"] = iso_date(update_data["event_date"])
    if "event_time" in update_data:
        update_data["event_time"] = iso_time(update_data["event_time"])

    if update_data:
        db.events.update_one({"_id": event_id}, {"$set": update_data})

    return with_id(db.events.find_one({"_id": event_id}))


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_event(event_id: int, current_user: CurrentUser = Depends(require_company), db: Database = Depends(get_db)):
    _own_event(db, event_id, current_user.id)

    db.events.delete_one({"_id": event_id})
    db.event_registrations.delete_many({"event_id": event_id})
    db.saved_items.delete_many({"item_type": "event", "item_id": event_id})
    log_activity(db, current_user.id, "event_deleted", {"event_id": event_id})

    return None


@router.get("/events/{event_id}/registrations", response_model=list[EventRegistrantResponse])
def get_event_registrations(
    event_id: int,
    current_user: CurrentUser = Depends(require_company),
    db: Database = Depends(get_db),
):
    _own_event(db, event_id, current_user.id)

    registrations = list(db.event_registrations.find({"event_id": event_id}).sort("registered_at", 1))
    ids = [r["student_id"] for r in registrations]
    profiles = {p["_id"]: p for p in db.student_profiles.find({"_id": {"$in": ids}})}
    emails = {u["_id"]: u["email"] for u in db.users.find({"_id": {"$in": ids}}, {"email": 1})}

    return [
        EventRegistrantResponse(
            registration_id=r["_id"],
            student_id=r["student_id"],
            full_name=profiles[r["student_id"]]["full_name"],
            email=emails[r["student_id"]],
            college=profiles[r["student_id"]].get("college"),
            major=profiles[r["student_id"]].get("major"),
            registered_at=r["registered_at"],
        )
        for r in registrations
        if r["student_id"] in profiles
    ]
