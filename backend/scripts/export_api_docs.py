"""
Exports API documentation to docs/api/:

  openapi.json                    the full OpenAPI 3 schema (what Swagger UI shows)
  pair4_handshake.postman_collection.json
                                  a Postman v2.1 collection with parameters,
                                  headers, and a saved sample response for
                                  each request, captured from the running API

Run with the backend up on PORT_BASE (9040) and the database seeded:

    backend/.venv/bin/python backend/scripts/export_api_docs.py
"""

import json

import httpx

from _common import REPO_ROOT

from app.main import app


BASE = "http://127.0.0.1:9040"
OUT_DIR = REPO_ROOT / "docs" / "api"
PASSWORD = "Pair4Demo!"

# (folder, name, method, path, role, body, query)
REQUESTS = [
    ("Auth", "Student login", "POST", "/auth/login", None, {"email": "demo.student@example.edu", "password": PASSWORD}, None),
    ("Auth", "Company login", "POST", "/auth/login", None, {"email": "demo.company@example.com", "password": PASSWORD}, None),
    ("Students", "My profile", "GET", "/students/me", "student", None, None),
    ("Students", "Search students (company Students tab)", "GET", "/students", "company", None, {"college": "San Jose State", "skill": "Python"}),
    ("Students", "Student public profile", "GET", "/students/52", "company", None, None),
    ("Jobs", "Search jobs", "GET", "/jobs", None, None, {"search": "Data", "category": "internship", "city": "San Jose"}),
    ("Jobs", "Job details", "GET", "/jobs/1", None, None, None),
    ("Applications", "My applications (filter by status)", "GET", "/applications/me", "student", None, {"status": "Pending"}),
    ("Events", "Upcoming events", "GET", "/events", "student", None, {"city": "Milpitas"}),
    ("Events", "Event details", "GET", "/events/1", "student", None, None),
    ("Events", "My registered events", "GET", "/events/registered", "student", None, None),
    ("Preferences", "My preferences", "GET", "/preferences/me", "student", None, None),
    ("Saved", "My saved items", "GET", "/saved", "student", None, None),
    ("Employer", "My job postings", "GET", "/employer/jobs", "company", None, None),
    ("Employer", "Applicants (filter by status)", "GET", "/employer/applications", "company", None, {"status": "Pending"}),
    ("Employer", "My events", "GET", "/employer/events", "company", None, None),
    ("Employer", "Company profile", "GET", "/employer/profile", "company", None, None),
    ("Assistant", "Chat with the assistant", "POST", "/assistant/chat", "student", {"message": "What are my saved preferences?"}, None),
]


def login(client, email):
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    response.raise_for_status()
    return response.json()["access_token"]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "openapi.json").write_text(json.dumps(app.openapi(), indent=2))

    client = httpx.Client(base_url=BASE, timeout=300)
    tokens = {
        "student": login(client, "demo.student@example.edu"),
        "company": login(client, "demo.company@example.com"),
    }

    folders = {}

    for folder, name, method, path, role, body, query in REQUESTS:
        headers = {"Content-Type": "application/json"}
        if role:
            headers["Authorization"] = f"Bearer {tokens[role]}"

        response = client.request(method, path, json=body, params=query, headers=headers)
        sample = response.json()
        if isinstance(sample, list):
            sample = sample[:2]  # keep the collection readable

        if "access_token" in str(sample):
            sample = {**sample, "access_token": "<jwt>"}

        postman_headers = [{"key": "Content-Type", "value": "application/json"}]
        if role:
            postman_headers.append({"key": "Authorization", "value": f"Bearer {{{{{role}_token}}}}"})

        request = {
            "method": method,
            "header": postman_headers,
            "url": {
                "raw": "{{base_url}}" + path + ("?" + "&".join(f"{k}={v}" for k, v in query.items()) if query else ""),
                "host": ["{{base_url}}"],
                "path": path.strip("/").split("/"),
                "query": [{"key": k, "value": str(v)} for k, v in (query or {}).items()],
            },
        }
        if body is not None:
            request["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2)}

        folders.setdefault(folder, []).append({
            "name": name,
            "request": request,
            "response": [{
                "name": f"{response.status_code} sample",
                "originalRequest": request,
                "status": response.reason_phrase,
                "code": response.status_code,
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": json.dumps(sample, indent=2, default=str),
            }],
        })
        print(f"{response.status_code} {method} {path}")

    collection = {
        "info": {
            "name": "Pair 4 Handshake API",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "description": "Lab 1 API. Log in with the Auth requests and paste the tokens into the student_token / company_token variables.",
        },
        "variable": [
            {"key": "base_url", "value": BASE},
            {"key": "student_token", "value": ""},
            {"key": "company_token", "value": ""},
        ],
        "item": [{"name": folder, "item": items} for folder, items in folders.items()],
    }

    (OUT_DIR / "pair4_handshake.postman_collection.json").write_text(json.dumps(collection, indent=2))
    print(f"wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
