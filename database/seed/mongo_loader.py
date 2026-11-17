"""
Turns relational rows (the Lab 1 MySQL table layout) into MongoDB
documents and loads them.

Used by:
- generate_seed.py: deterministic seed rows -> MongoDB
- migrate_mysql_to_mongo.py: rows read from the Lab 1 MySQL database -> MongoDB

Mapping (MySQL table -> MongoDB collection):
  users                    -> users                  (_id = users.id)
  student_profiles         -> student_profiles       (_id = user_id, skills embedded as names)
  student_skills           -> student_profiles.skills
  company_profiles         -> company_profiles       (_id = user_id)
  skills                   -> skills
  jobs + job_skills        -> jobs                   (company_name and skills embedded)
  applications             -> applications           (resume PDF in GridFS bucket "resumes")
  events                   -> events                 (company_name embedded)
  event_registrations      -> event_registrations
  student_preferences      -> student_preferences    (_id = student_id)
  saved_items              -> saved_items
  (new) sessions, activity_logs, assistant_rules, student_memory, assistant_sessions,
        notifications, processed_events, traces, dead_letters, counters
"""

import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.database import ensure_indexes, iso_date, iso_time, resume_bucket, set_counter  # noqa: E402


COLLECTIONS = [
    "users", "student_profiles", "company_profiles", "skills", "jobs", "applications",
    "events", "event_registrations", "student_preferences", "saved_items", "sessions",
    "activity_logs", "assistant_rules", "student_memory", "assistant_sessions",
    "notifications", "processed_events", "traces", "dead_letters", "memory_consolidations",
    "counters", "resumes.files", "resumes.chunks", "pictures.files", "pictures.chunks",
]


def _dt(value):
    """
    MySQL DATETIME -> naive datetime; DATE -> ISO string handled separately.
    """

    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time())
    return value


def _float(value):
    return float(value) if value is not None else None


def _time(value):
    # pymysql returns TIME columns as timedelta.
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
        return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"
    return iso_time(value)


def rows_to_documents(rows: dict[str, list[tuple]]) -> dict[str, list[dict]]:
    skill_names = {skill_id: name for skill_id, name in rows["skills"]}
    student_skills = defaultdict(list)
    for student_id, skill_id in rows["student_skills"]:
        student_skills[student_id].append(skill_names[skill_id])
    job_skills = defaultdict(list)
    for job_id, skill_id in rows["job_skills"]:
        job_skills[job_id].append(skill_names[skill_id])

    company_names = {row[0]: row[1] for row in rows["company_profiles"]}

    docs: dict[str, list[dict]] = {}

    docs["users"] = [
        {"_id": uid, "email": email, "password_hash": pw, "user_role": role, "created_at": _dt(c), "updated_at": _dt(u)}
        for uid, email, pw, role, c, u in rows["users"]
    ]

    docs["company_profiles"] = [
        {"_id": uid, "company_name": name, "location": loc, "description": desc, "contact_email": cemail,
         "contact_phone": cphone, "profile_picture_path": None, "created_at": _dt(c), "updated_at": _dt(u)}
        for uid, name, loc, desc, cemail, cphone, c, u in rows["company_profiles"]
    ]

    docs["student_profiles"] = [
        {"_id": uid, "full_name": name, "date_of_birth": iso_date(dob), "city": city, "state": state,
         "country": country, "career_objective": objective, "college": college, "degree": degree,
         "major": major, "graduation_year": grad, "cgpa": _float(cgpa), "experience": exp, "phone": phone,
         "profile_picture_path": None, "skills": sorted(student_skills[uid], key=str.lower),
         "created_at": _dt(c), "updated_at": _dt(u)}
        for (uid, name, dob, city, state, country, objective, college, degree, major, grad, cgpa, exp, phone, c, u)
        in rows["student_profiles"]
    ]

    docs["skills"] = [{"_id": sid, "skill_name": name, "name_lower": name.lower()} for sid, name in rows["skills"]]

    docs["jobs"] = [
        {"_id": jid, "company_id": cid, "company_name": company_names.get(cid, ""), "title": title,
         "posted_date": iso_date(posted), "deadline": iso_date(deadline), "location": loc, "is_remote": bool(remote),
         "salary_min": _float(smin), "salary_max": _float(smax), "description": desc, "category": cat,
         "skills": sorted(job_skills[jid], key=str.lower), "created_at": _dt(c), "updated_at": _dt(u)}
        for jid, cid, title, posted, deadline, loc, remote, smin, smax, desc, cat, c, u in rows["jobs"]
    ]

    docs["applications"] = [
        {"_id": aid, "student_id": sid, "job_id": jid, "resume_path": path, "applied_at": _dt(applied),
         "status": status, "updated_at": _dt(updated)}
        for aid, sid, jid, path, applied, status, updated in rows["applications"]
    ]

    docs["events"] = [
        {"_id": eid, "company_id": cid, "company_name": company_names.get(cid, ""), "event_name": name,
         "description": desc, "event_date": iso_date(edate), "event_time": _time(etime), "location": loc,
         "eligibility": elig, "created_at": _dt(c)}
        for eid, cid, name, desc, edate, etime, loc, elig, c in rows["events"]
    ]

    docs["event_registrations"] = [
        {"_id": rid, "student_id": sid, "event_id": eid, "registered_at": _dt(at)}
        for rid, sid, eid, at in rows["event_registrations"]
    ]

    docs["student_preferences"] = [
        {"_id": sid, "preferred_city": city, "preferred_category": cat, "minimum_salary": _float(minsal),
         "preferred_work_mode": mode, "preferred_major": major, "preferred_event_major": emajor, "updated_at": _dt(u)}
        for sid, city, cat, minsal, mode, major, emajor, u in rows["student_preferences"]
    ]

    docs["saved_items"] = [
        {"_id": iid, "student_id": sid, "item_type": itype, "item_id": item, "saved_at": _dt(at)}
        for iid, sid, itype, item, at in rows.get("saved_items", [])
    ]

    return docs


def load_documents(db, docs: dict[str, list[dict]], reset: bool) -> None:
    if reset:
        for name in COLLECTIONS:
            db.drop_collection(name)
    elif db.users.estimated_document_count():
        raise SystemExit(f"{db.name} already has data. Re-run with --reset to rebuild it.")

    for name, documents in docs.items():
        if documents:
            db[name].insert_many(documents, ordered=False)

    # Next ids continue after the loaded rows.
    for name in ["users", "jobs", "applications", "events", "event_registrations", "saved_items"]:
        highest = max((d["_id"] for d in docs.get(name, [])), default=0)
        set_counter(db, name, highest)

    ensure_indexes(db)


def store_resume_file(db, relative_path: str, contents: bytes) -> None:
    """
    Puts a resume PDF into GridFS under the filename the application row uses.
    """

    bucket = resume_bucket(db)
    name = relative_path.rsplit("/", 1)[-1]
    for existing in bucket.find({"filename": name}):
        bucket.delete(existing._id)
    bucket.upload_from_stream(name, contents, metadata={"contentType": "application/pdf", "seeded": True})
