"""
API tests through FastAPI's TestClient against the seeded database.

Run from backend/ after database/seed/generate_seed.py --reset:

    .venv/bin/python -m pytest -q
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Application, Event, Job


client = TestClient(app)
PASSWORD = "Pair4Demo!"


def token(email):
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="module")
def student():
    return token("demo.student@example.edu")


@pytest.fixture(scope="module")
def company():
    return token("demo.company@example.com")


def test_login_rejects_wrong_password():
    response = client.post("/auth/login", json={"email": "demo.student@example.edu", "password": "wrong-password"})
    assert response.status_code == 401


def test_signup_validates_input():
    response = client.post("/auth/signup", json={"full_name": "X", "email": "bad", "password": "short", "college": "S"})
    assert response.status_code == 422


def test_protected_routes_need_a_token():
    assert client.get("/students/me").status_code == 401
    assert client.get("/employer/jobs").status_code == 401


def test_roles_are_enforced(student, company):
    assert client.get("/employer/jobs", headers=student).status_code == 403
    assert client.post("/assistant/chat", json={"message": "hi"}, headers=company).status_code == 403


def test_job_search_filters():
    jobs = client.get("/jobs", params={"category": "internship", "city": "San Jose"}).json()
    assert jobs and all(j["category"] == "internship" and "San Jose" in j["location"] for j in jobs)
    assert all(date.fromisoformat(j["deadline"]) >= date.today() for j in jobs)
    assert client.get("/jobs", params={"category": "volunteer"}).status_code == 422


def test_job_details_and_missing_job():
    assert client.get("/jobs/1").json()["company_name"]
    assert client.get("/jobs/999999").status_code == 404


def test_application_status_filter(student):
    rows = client.get("/applications/me", params={"status": "Pending"}, headers=student).json()
    assert all(r["status"] == "Pending" for r in rows)


def test_events_are_upcoming_and_sorted(student):
    events = client.get("/events", headers=student).json()
    dates = [e["event_date"] for e in events]
    assert dates == sorted(dates) and all(date.fromisoformat(d) >= date.today() for d in dates)
    assert all(e["is_eligible"] is not None for e in events)


def test_ineligible_registration_is_refused(student):
    events = client.get("/events", headers=student).json()
    blocked = next(e for e in events if e["is_eligible"] is False)
    response = client.post(f"/events/{blocked['id']}/register", headers=student)
    assert response.status_code == 403


def test_student_directory_filters(student):
    rows = client.get("/students", params={"major": "Data Science", "skill": "python"}, headers=student).json()
    assert rows and all("Data Science" in r["major"] and "Python" in r["skills"] for r in rows)


def test_company_sees_only_its_own_applications(company):
    db = SessionLocal()
    try:
        other = db.query(Application).join(Job).filter(Job.company_id != 1).first()
        mine = db.query(Application).join(Job).filter(Job.company_id == 1).first()
    finally:
        db.close()

    assert client.get(f"/employer/applications/{other.id}", headers=company).status_code == 404
    assert client.get(f"/employer/applications/{other.id}/resume", headers=company).status_code == 404

    resume = client.get(f"/employer/applications/{mine.id}/resume", headers=company)
    assert resume.status_code == 200 and resume.headers["content-type"] == "application/pdf"


def test_status_update_validates_value(company):
    db = SessionLocal()
    try:
        mine = db.query(Application).join(Job).filter(Job.company_id == 1).first()
    finally:
        db.close()

    url = f"/employer/applications/{mine.id}/status"
    assert client.patch(url, json={"status": "Hired"}, headers=company).status_code == 422
    assert client.patch(url, json={"status": mine.status}, headers=company).json()["status"] == mine.status


def test_event_registrations_are_owner_only(company):
    db = SessionLocal()
    try:
        other_event = db.query(Event).filter(Event.company_id != 1).first()
        my_event = db.query(Event).filter(Event.company_id == 1).first()
    finally:
        db.close()

    assert client.get(f"/employer/events/{other_event.id}/registrations", headers=company).status_code == 404
    assert client.get(f"/employer/events/{my_event.id}/registrations", headers=company).status_code == 200


def test_picture_upload_rejects_non_images(student):
    response = client.post(
        "/students/me/picture",
        files={"picture": ("notes.png", b"not really a png", "image/png")},
        headers=student,
    )
    assert response.status_code == 400
