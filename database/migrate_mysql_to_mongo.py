"""
Migrates the Lab 1 MySQL database (p4_handshake) to MongoDB.

Reads every table with the same column order the Lab 1 seed used, turns
the rows into documents with database/seed/mongo_loader.py (the converter
the Lab 2 seed generator also uses), copies resume PDFs from
backend/uploads/ into GridFS, and verifies the counts.

    docker start p4-mysql
    backend/.venv/bin/python database/migrate_mysql_to_mongo.py --target p4_handshake_migrated

Passwords stay bcrypt hashes; they are copied, never decrypted.
"""

import argparse
import os
import sys
from pathlib import Path

import pymysql

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "database" / "seed"))
sys.path.insert(0, str(REPO / "backend"))

from app.database import get_client  # noqa: E402
from mongo_loader import load_documents, rows_to_documents, store_resume_file  # noqa: E402

TABLES = {
    "users": "id, email, password_hash, user_role, created_at, updated_at",
    "company_profiles": "user_id, company_name, location, description, contact_email, contact_phone, created_at, updated_at",
    "student_profiles": "user_id, full_name, date_of_birth, city, state, country, career_objective, college, degree, "
                        "major, graduation_year, cgpa, experience, phone, created_at, updated_at",
    "skills": "id, skill_name",
    "student_skills": "student_id, skill_id",
    "jobs": "id, company_id, title, posted_date, deadline, location, is_remote, salary_min, salary_max, description, "
            "category, created_at, updated_at",
    "job_skills": "job_id, skill_id",
    "applications": "id, student_id, job_id, resume_path, applied_at, status, updated_at",
    "events": "id, company_id, event_name, description, event_date, event_time, location, eligibility, created_at",
    "event_registrations": "id, student_id, event_id, registered_at",
    "student_preferences": "student_id, preferred_city, preferred_category, minimum_salary, preferred_work_mode, "
                           "preferred_major, preferred_event_major, updated_at",
    "saved_items": "id, student_id, item_type, item_id, saved_at",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default="p4_handshake_migrated", help="MongoDB database to write")
    args = parser.parse_args()

    mysql = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"), port=int(os.getenv("MYSQL_PORT", "3307")),
        user=os.getenv("MYSQL_USER", "root"), password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "p4_handshake"), charset="utf8mb4",
    )
    rows = {}
    with mysql.cursor() as cursor:
        for table, columns in TABLES.items():
            cursor.execute(f"SELECT {columns} FROM {table}")
            rows[table] = list(cursor.fetchall())
    mysql.close()

    docs = rows_to_documents(rows)
    db = get_client()[args.target]
    load_documents(db, docs, reset=True)

    uploads = REPO / "backend"
    copied = 0
    for path in {d["resume_path"] for d in docs["applications"]}:
        file = uploads / path
        if file.is_file():
            store_resume_file(db, path, file.read_bytes())
            copied += 1

    print(f"Migrated MySQL p4_handshake -> MongoDB {args.target}")
    print(f"{'table':<22}{'MySQL rows':>11}  {'collection':<22}{'documents':>10}")
    mapping = {"student_skills": "student_profiles.skills", "job_skills": "jobs.skills"}
    for table in TABLES:
        target = mapping.get(table, table)
        count = db[table].count_documents({}) if table not in mapping else "embedded"
        print(f"{table:<22}{len(rows[table]):>11}  {target:<22}{count:>10}")
    print(f"resume files copied to GridFS: {copied}")


if __name__ == "__main__":
    main()
