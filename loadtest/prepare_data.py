"""
Test data for the JMeter plan, from the seeded MongoDB:
  data/students.csv        all 200 seeded student emails (password Pair4Demo!)
  data/search_terms.csv    title/company/event words that match seeded data
  data/apply_<N>.csv       N (student, open job) pairs nobody has applied to yet,
                           disjoint across levels, so every submission is new
  data/resume.pdf          a small valid PDF

    backend/.venv/bin/python loadtest/prepare_data.py
"""

import csv
import random
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
from app.database import get_database  # noqa: E402

LEVELS = [100, 200, 300, 400, 500]


def main():
    db = get_database()
    data = HERE / "data"
    data.mkdir(exist_ok=True)
    rng = random.Random(4)

    students = [(u["_id"], u["email"]) for u in db.users.find({"user_role": "student", "email": {"$regex": "@example.edu$"}}).sort("_id", 1)]
    with open(data / "students.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["email"]); w.writerows([[e] for _, e in students])

    terms = ["data", "intern", "engineer", "analyst", "software", "career", "workshop", "TechNova", "Cloud", "design"]
    with open(data / "search_terms.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["term"]); w.writerows([[t] for t in terms])

    open_jobs = [j["_id"] for j in db.jobs.find({"deadline": {"$gte": date.today().isoformat()}}, {"_id": 1})]
    applied = {(a["student_id"], a["job_id"]) for a in db.applications.find({}, {"student_id": 1, "job_id": 1})}
    pairs = [(sid, email, jid) for sid, email in students for jid in open_jobs if (sid, jid) not in applied]
    rng.shuffle(pairs)

    start = 0
    for level in LEVELS:
        chunk = pairs[start:start + level]
        start += level
        with open(data / f"apply_{level}.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["email", "job_id"]); w.writerows([[e, j] for _, e, j in chunk])

    (data / "resume.pdf").write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    print(f"{len(students)} students, {len(open_jobs)} open jobs, {start} fresh application pairs across {LEVELS}")


if __name__ == "__main__":
    main()
