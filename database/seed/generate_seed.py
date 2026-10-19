"""
Seed generator for the Pair 4 Handshake lab.

Creates 50 companies, 200 students, 320 jobs, 1,500 applications,
110 events, plus skills, preferences, and event registrations across
CITY_SET. Every random choice comes from random.Random(SEED), so the
same SEED always produces the same rows. Dates are offsets from the
anchor date (today by default) so events stay "upcoming" whenever the
script is run; pass --anchor-date to pin them.

Usage, from the repository root with MySQL running and .env filled in:

    backend/.venv/bin/python database/seed/generate_seed.py --reset

--reset drops p4_handshake, recreates it from database/schema.sql,
and then loads the seed rows.
"""

import argparse
import os
import random
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import bcrypt
import pymysql
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
SCHEMA_FILE = REPO_ROOT / "database" / "schema.sql"
UPLOAD_DIR = BACKEND_DIR / "uploads"

load_dotenv(REPO_ROOT / ".env")

# The eligibility rule lives in the backend so registration,
# the assistant, and the seed data all agree on it.
sys.path.insert(0, str(BACKEND_DIR))
from app.eligibility import is_student_eligible  # noqa: E402


PAIR = int(os.getenv("PAIR", "4"))
SEED = int(os.getenv("SEED", str(PAIR)))
DATABASE = os.getenv("MYSQL_DATABASE", f"p{PAIR}_handshake")

CITY_SET = ["San Jose", "Santa Clara", "Milpitas"]
STATE = "CA"

# All seeded accounts share this password so graders can log in.
DEMO_PASSWORD = "Pair4Demo!"

COUNTS = {
    "companies": 50,
    "students": 200,
    "jobs": 320,
    "applications": 1500,
    "events": 110,
}


COMPANY_NAMES = [
    "TechNova Solutions", "DataBridge Analytics", "Silicon Orchard Labs",
    "BlueRiver Cloud", "Quantum Leaf Systems", "Redwood Robotics",
    "CircuitPath Semiconductors", "Golden Gate Fintech", "Valley Health AI",
    "Summit Storage Inc", "Bayline Logistics", "Nimbus Data Works",
    "Pinecrest Security", "Lumen Devices", "Harborview Media",
    "Copperline Networks", "Evergreen Energy Tech", "Mosaic Learning",
    "Northstar Payments", "Brightpath Retail", "Cedar Peak Software",
    "Atlas Mobility", "Sierra Sensor Co", "Orchid Biotech",
    "Keystone Analytics", "Ironwood Manufacturing", "Polaris Cloud Services",
    "Riverbend Consulting", "Skyline Games", "Trident Chips",
    "Wavelength Wireless", "Zephyr Drones", "Alder Insights",
    "Beacon Civic Tech", "Cobalt DevTools", "Driftwood Design Studio",
    "Elm Street Bank", "Foxglove Health", "Granite Data Systems",
    "Horizon EdTech", "Indigo Marketing Group", "Juniper Supply Chain",
    "Kestrel Aerospace", "Lakeside Insurance", "Meridian Hardware",
    "Nova Campus Services", "Opal Commerce", "Prism Vision AI",
    "Quarry Construction Tech", "Ridgeline Media Labs",
]

INDUSTRIES = [
    "cloud computing", "data analytics", "semiconductors", "fintech",
    "healthcare technology", "robotics", "cybersecurity", "consumer electronics",
    "education technology", "logistics", "media", "renewable energy",
]

SKILLS = [
    "Python", "SQL", "Java", "JavaScript", "React", "FastAPI", "Node.js",
    "Machine Learning", "Data Analysis", "Tableau", "Excel", "AWS", "Docker",
    "Kubernetes", "Spark", "Kafka", "Pandas", "TensorFlow", "PyTorch",
    "Statistics", "R", "C++", "Git", "Linux", "Figma", "Communication",
    "Customer Service", "Marketing", "Financial Modeling", "CAD",
]

# major -> skills a student in that major is likely to list
MAJORS = {
    "Computer Science": ["Python", "Java", "C++", "SQL", "Git", "Linux", "React", "JavaScript", "Docker"],
    "Data Science": ["Python", "SQL", "Pandas", "Machine Learning", "Statistics", "Tableau", "Spark", "R"],
    "Software Engineering": ["Java", "JavaScript", "React", "Node.js", "Git", "Docker", "AWS", "FastAPI"],
    "Computer Engineering": ["C++", "Python", "Linux", "Git", "Docker"],
    "Electrical Engineering": ["C++", "Python", "CAD", "Linux"],
    "Mechanical Engineering": ["CAD", "Python", "Excel"],
    "Business Analytics": ["SQL", "Excel", "Tableau", "Data Analysis", "Python", "Communication"],
    "Statistics": ["R", "Python", "Statistics", "SQL", "Data Analysis"],
    "Marketing": ["Marketing", "Communication", "Excel", "Figma"],
    "Finance": ["Financial Modeling", "Excel", "SQL", "Communication"],
    "Graphic Design": ["Figma", "Communication", "Marketing"],
}

COLLEGES = [
    "San Jose State University",
    "Santa Clara University",
    "Mission College",
    "Evergreen Valley College",
    "De Anza College",
]

DEGREES = ["B.S.", "B.S.", "B.S.", "M.S.", "B.A."]

FIRST_NAMES = [
    "Aarav", "Maya", "Ethan", "Priya", "Lucas", "Sofia", "Noah", "Ananya",
    "Liam", "Isabella", "Arjun", "Emma", "Mateo", "Chloe", "Rohan", "Olivia",
    "Kai", "Mei", "Diego", "Sara", "Vikram", "Grace", "Omar", "Hana",
    "Daniel", "Leila", "Jin", "Nora", "Ravi", "Elena", "Samuel", "Aisha",
    "Kevin", "Zara", "Tyler", "Divya", "Marcus", "Yuki", "Andre", "Fatima",
]

LAST_NAMES = [
    "Patel", "Nguyen", "Garcia", "Kim", "Chen", "Singh", "Lopez", "Smith",
    "Reddy", "Johnson", "Wang", "Martinez", "Kumar", "Brown", "Tran", "Lee",
    "Hernandez", "Shah", "Davis", "Park", "Rao", "Wilson", "Ali", "Lin",
    "Gonzalez", "Iyer", "Thomas", "Huang", "Moore", "Pham",
]

# (title, category, skills) templates. Category is one of the four
# schema values; salary units follow the category (see make_salary).
JOB_TEMPLATES = [
    ("Data Science Intern", "internship", ["Python", "Pandas", "Machine Learning", "SQL", "Statistics"]),
    ("Machine Learning Intern", "internship", ["Python", "PyTorch", "TensorFlow", "Machine Learning"]),
    ("Software Engineering Intern", "internship", ["Python", "Java", "Git", "SQL"]),
    ("Frontend Developer Intern", "internship", ["React", "JavaScript", "Figma", "Git"]),
    ("Backend Developer Intern", "internship", ["Python", "FastAPI", "SQL", "Docker"]),
    ("Data Analyst Intern", "internship", ["SQL", "Excel", "Tableau", "Data Analysis"]),
    ("Cloud Engineering Intern", "internship", ["AWS", "Docker", "Linux", "Kubernetes"]),
    ("Hardware Test Intern", "internship", ["C++", "Linux", "CAD"]),
    ("Marketing Intern", "internship", ["Marketing", "Communication", "Figma"]),
    ("Financial Analyst Intern", "internship", ["Financial Modeling", "Excel", "SQL"]),
    ("UX Design Intern", "internship", ["Figma", "Communication"]),
    ("Mechanical Design Intern", "internship", ["CAD", "Excel"]),
    ("Software Engineer", "full_time", ["Java", "Python", "Git", "Docker", "AWS"]),
    ("Data Engineer", "full_time", ["Python", "SQL", "Spark", "Kafka", "AWS"]),
    ("Data Scientist", "full_time", ["Python", "Machine Learning", "Statistics", "SQL"]),
    ("Business Intelligence Analyst", "full_time", ["SQL", "Tableau", "Excel", "Data Analysis"]),
    ("DevOps Engineer", "full_time", ["Docker", "Kubernetes", "Linux", "AWS"]),
    ("QA Engineer", "full_time", ["Python", "Git", "Linux"]),
    ("Associate Product Marketing Manager", "full_time", ["Marketing", "Communication", "Excel"]),
    ("Junior Financial Analyst", "full_time", ["Financial Modeling", "Excel"]),
    ("Part-Time Web Developer", "part_time", ["JavaScript", "React", "Node.js"]),
    ("Part-Time Data Entry Assistant", "part_time", ["Excel", "Communication"]),
    ("Customer Support Associate", "part_time", ["Customer Service", "Communication"]),
    ("Social Media Assistant", "part_time", ["Marketing", "Communication", "Figma"]),
    ("Campus IT Help Desk Assistant", "on_campus", ["Linux", "Customer Service", "Communication"]),
    ("Library Research Assistant", "on_campus", ["Excel", "Communication"]),
    ("Teaching Assistant - Data Structures", "on_campus", ["Java", "C++", "Communication"]),
    ("Student Data Lab Assistant", "on_campus", ["Python", "SQL", "Data Analysis"]),
    ("Campus Recreation Front Desk", "on_campus", ["Customer Service", "Communication"]),
]

EVENT_TEMPLATES = [
    ("Bay Area Tech Career Fair", "Meet recruiters from local tech companies hiring interns and new grads.", "All majors"),
    ("Data Science Networking Night", "Talk with data scientists about projects, tools, and career paths.", "Data Science and Statistics students"),
    ("Resume Review Workshop", "Bring a printed resume and get one-on-one feedback from recruiters.", "All majors"),
    ("Mock Technical Interview Day", "Practice coding interviews with engineers and get written feedback.", "Computer Science and Software Engineering students"),
    ("Cloud Computing Bootcamp", "A hands-on afternoon deploying a small service to the cloud.", "Computer Science students"),
    ("Women in Engineering Panel", "A panel of engineers sharing career stories and advice.", "Engineering students"),
    ("Startup Pitch Night", "Founders pitch their companies and recruit early hires.", "All majors"),
    ("Machine Learning Paper Reading Group", "Discuss a recent ML paper with the company research team.", "Computer Science and Data Science students"),
    ("Finance Careers Info Session", "Learn about analyst programs and the recruiting timeline.", "Finance and Business Analytics students"),
    ("Design Portfolio Review", "Designers review student portfolios and share hiring tips.", "Graphic Design students"),
    ("Hackathon Kickoff", "Form teams and start a 24-hour build with company mentors.", "Computer Science students"),
    ("Graduating Seniors Hiring Mixer", "Meet hiring managers looking for full-time new grads.", "Graduating seniors (class of 2027)"),
    ("Marketing Analytics Workshop", "Learn how marketing teams use data to plan campaigns.", "Marketing and Business Analytics students"),
    ("Hardware Lab Open House", "Tour the hardware lab and meet the validation team.", "Electrical Engineering and Computer Engineering students"),
]

VENUES = {
    "San Jose": ["SJSU Student Union", "San Jose Convention Center", "SJSU Engineering Building", "Downtown San Jose Innovation Hub"],
    "Santa Clara": ["Santa Clara University Benson Center", "Santa Clara Convention Center", "Mission City Tech Hall"],
    "Milpitas": ["Milpitas Library Auditorium", "Milpitas Community Center", "Great Mall Conference Room"],
}

SAMPLE_RESUME_NAME = "seed_resume.pdf"


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def location_for(city):
    return f"{city}, {STATE}"


def make_salary(rng, category, title):
    """
    Internship, part-time, and on-campus pay is hourly; full-time pay is
    annual. Search output labels the unit so comparisons stay honest.
    """
    if category == "full_time":
        low = rng.randrange(85_000, 150_001, 5_000)
        return float(low), float(low + rng.randrange(10_000, 40_001, 5_000))

    if category == "internship":
        low = rng.randrange(22, 52)
        if "Machine Learning" in title or "Data Science" in title:
            low += 6
        return float(low), float(low + rng.randrange(4, 15))

    low = rng.randrange(17, 28)
    return float(low), float(low + rng.randrange(2, 8))


def write_sample_resume():
    """
    Every seeded application points at one small, valid PDF so the
    company resume preview works for seed data too.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / SAMPLE_RESUME_NAME
    stream = b"BT /F1 18 Tf 72 720 Td (Sample seeded resume - Pair 4 Handshake lab) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))
    return f"uploads/{SAMPLE_RESUME_NAME}"


def connect(database=None):
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=database,
        charset="utf8mb4",
        autocommit=False,
    )


def apply_schema(reset):
    """
    Runs database/schema.sql statement by statement.
    """
    sql = SCHEMA_FILE.read_text()
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", "", sql)
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    connection = connect()
    try:
        with connection.cursor() as cursor:
            if reset:
                cursor.execute(f"DROP DATABASE IF EXISTS `{DATABASE}`")
            for statement in statements:
                cursor.execute(statement)
        connection.commit()
    finally:
        connection.close()


def build_rows(anchor):
    rng = random.Random(SEED)
    password_hash = bcrypt.hashpw(DEMO_PASSWORD.encode(), bcrypt.gensalt(rounds=10)).decode()
    now = datetime.combine(anchor, time(9, 0))

    rows = {name: [] for name in [
        "users", "company_profiles", "student_profiles", "skills",
        "student_skills", "jobs", "job_skills", "applications", "events",
        "event_registrations", "student_preferences", "saved_items",
    ]}

    skill_ids = {name: index for index, name in enumerate(SKILLS, start=1)}
    rows["skills"] = [(skill_id, name) for name, skill_id in skill_ids.items()]

    # Companies: user ids 1..50. The first one is the demo company login.
    company_ids = []
    for index, name in enumerate(COMPANY_NAMES[:COUNTS["companies"]], start=1):
        city = CITY_SET[(index - 1) % len(CITY_SET)]
        email = "demo.company@example.com" if index == 1 else f"careers@{slugify(name)}.example.com"
        rows["users"].append((index, email, password_hash, "company", now, now))
        industry = rng.choice(INDUSTRIES)
        rows["company_profiles"].append((
            index, name, location_for(city),
            f"{name} is a {industry} company based in {city} that hires students and new graduates.",
            f"careers@{slugify(name)}.example.com",
            f"408-555-{1000 + index:04d}",
            now, now,
        ))
        company_ids.append(index)

    company_city = {cid: CITY_SET[(cid - 1) % len(CITY_SET)] for cid in company_ids}

    # Students: user ids 51..250. The first two are demo logins: one with
    # preferences and one without, for the "no preferences" tool path.
    student_ids = []
    student_info = {}
    major_names = list(MAJORS)
    first_student_id = COUNTS["companies"] + 1
    for offset in range(COUNTS["students"]):
        user_id = first_student_id + offset
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        if offset == 0:
            first, last, email = "Demo", "Student", "demo.student@example.edu"
            major, city, college, grad_year = "Computer Science", "San Jose", "San Jose State University", 2027
        elif offset == 1:
            first, last, email = "NoPrefs", "Student", "noprefs.student@example.edu"
            major, city, college, grad_year = "Data Science", "Santa Clara", "Santa Clara University", 2028
        else:
            email = f"{first.lower()}.{last.lower()}{offset}@example.edu"
            major = rng.choice(major_names)
            city = rng.choice(CITY_SET)
            college = rng.choice(COLLEGES)
            grad_year = rng.randint(2026, 2029)

        dob = date(grad_year - 22, rng.randint(1, 12), rng.randint(1, 28))
        cgpa = round(rng.uniform(2.6, 4.0), 2)
        rows["users"].append((user_id, email, password_hash, "student", now, now))
        rows["student_profiles"].append((
            user_id, f"{first} {last}", dob, city, STATE, "USA",
            f"{major} student looking for hands-on experience in {rng.choice(INDUSTRIES)}.",
            college, rng.choice(DEGREES), major, grad_year, cgpa,
            rng.choice([
                "Teaching assistant for an intro programming course.",
                "Summer internship building internal dashboards.",
                "Led a student club project team of five.",
                "Part-time retail associate for two years.",
                "Research assistant in a campus lab.",
                None,
            ]),
            f"669-555-{rng.randint(0, 9999):04d}",
            now, now,
        ))

        pool = MAJORS[major]
        chosen = rng.sample(pool, k=min(len(pool), rng.randint(3, 5)))
        if rng.random() < 0.4:
            chosen.append(rng.choice(SKILLS))
        for skill in sorted(set(chosen)):
            rows["student_skills"].append((user_id, skill_ids[skill]))

        student_ids.append(user_id)
        student_info[user_id] = {"major": major, "graduation_year": grad_year, "city": city}

    # Preferences for ~70% of students (never for the "no prefs" demo).
    for user_id in student_ids:
        if user_id == first_student_id:
            rows["student_preferences"].append((
                user_id, "San Jose", "internship", 25.0, "onsite",
                "Computer Science", "Computer Science", now,
            ))
            continue
        if user_id == first_student_id + 1 or rng.random() > 0.7:
            continue
        info = student_info[user_id]
        rows["student_preferences"].append((
            user_id,
            info["city"],
            rng.choice(["internship", "internship", "full_time", "part_time", "on_campus"]),
            float(rng.choice([18, 20, 25, 30, 35])),
            rng.choice(["remote", "onsite", "hybrid"]),
            info["major"],
            info["major"],
            now,
        ))

    # Jobs. A handful of remote Data Science internships are guaranteed
    # so the "remote data science internship" transcript has real matches.
    job_ids = []
    for job_id in range(1, COUNTS["jobs"] + 1):
        if job_id <= 4:
            title, category, pool = JOB_TEMPLATES[0]
            remote = True
        else:
            title, category, pool = rng.choice(JOB_TEMPLATES)
            remote = rng.random() < 0.15
        company_id = rng.choice(company_ids)
        city = company_city[company_id] if rng.random() < 0.7 else rng.choice(CITY_SET)
        salary_min, salary_max = make_salary(rng, category, title)
        posted = anchor - timedelta(days=rng.randint(0, 60))
        deadline = anchor + timedelta(days=rng.randint(-10, 90))
        required = rng.sample(pool, k=min(len(pool), rng.randint(2, 4)))
        company_name = COMPANY_NAMES[company_id - 1]
        description = (
            f"{company_name} is hiring a {title} "
            f"{'(remote)' if remote else 'in ' + city}. "
            f"You will work with {', '.join(required)} on real projects with a mentor. "
            f"Contact careers@{slugify(company_name)}.example.com with questions."
        )
        rows["jobs"].append((
            job_id, company_id, title, posted, deadline,
            "Remote" if remote else location_for(city),
            remote, salary_min, salary_max, description, category, now, now,
        ))
        for skill in sorted(set(required)):
            rows["job_skills"].append((job_id, skill_ids[skill]))
        job_ids.append(job_id)

    # Applications: unique (student, job) pairs.
    resume_path = write_sample_resume()
    pairs = set()
    while len(pairs) < COUNTS["applications"]:
        pairs.add((rng.choice(student_ids), rng.choice(job_ids)))
    for app_id, (student_id, job_id) in enumerate(sorted(pairs), start=1):
        applied = now - timedelta(days=rng.randint(0, 45), hours=rng.randint(0, 23))
        status = rng.choices(["Pending", "Reviewed", "Declined"], weights=[50, 30, 20])[0]
        rows["applications"].append((app_id, student_id, job_id, resume_path, applied, status, applied))

    # Events. The first few are Computer Science events next month so the
    # "event for computer science students next month" transcript has data.
    next_month_start = (anchor.replace(day=1) + timedelta(days=32)).replace(day=1)
    event_ids = []
    event_eligibility = {}
    for event_id in range(1, COUNTS["events"] + 1):
        if event_id <= 3:
            name, description, eligibility = EVENT_TEMPLATES[[3, 4, 10][event_id - 1]]
            event_date = next_month_start + timedelta(days=rng.randint(2, 25))
        else:
            name, description, eligibility = rng.choice(EVENT_TEMPLATES)
            event_date = anchor + timedelta(days=rng.randint(-20, 100))
        company_id = rng.choice(company_ids)
        city = rng.choice(CITY_SET)
        venue = rng.choice(VENUES[city])
        company_name = COMPANY_NAMES[company_id - 1]
        rows["events"].append((
            event_id, company_id, f"{company_name} {name}",
            f"{description} Hosted by {company_name}.",
            event_date,
            time(rng.choice([10, 12, 14, 16, 17, 18]), rng.choice([0, 30])),
            f"{venue}, {city}, {STATE}",
            eligibility,
            now,
        ))
        event_ids.append(event_id)
        event_eligibility[event_id] = eligibility

    # Registrations only where the student is eligible.
    registrations = set()
    attempts = 0
    while len(registrations) < 600 and attempts < 20_000:
        attempts += 1
        student_id = rng.choice(student_ids)
        event_id = rng.choice(event_ids)
        info = student_info[student_id]
        if is_student_eligible(event_eligibility[event_id], info["major"], info["graduation_year"]):
            registrations.add((student_id, event_id))
    for reg_id, (student_id, event_id) in enumerate(sorted(registrations), start=1):
        rows["event_registrations"].append((reg_id, student_id, event_id, now))

    return rows


INSERTS = {
    "users": "INSERT INTO users (id, email, password_hash, user_role, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s)",
    "company_profiles": "INSERT INTO company_profiles (user_id, company_name, location, description, contact_email, contact_phone, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
    "student_profiles": "INSERT INTO student_profiles (user_id, full_name, date_of_birth, city, state, country, career_objective, college, degree, major, graduation_year, cgpa, experience, phone, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
    "skills": "INSERT INTO skills (id, skill_name) VALUES (%s,%s)",
    "student_skills": "INSERT INTO student_skills (student_id, skill_id) VALUES (%s,%s)",
    "jobs": "INSERT INTO jobs (id, company_id, title, posted_date, deadline, location, is_remote, salary_min, salary_max, description, category, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
    "job_skills": "INSERT INTO job_skills (job_id, skill_id) VALUES (%s,%s)",
    "applications": "INSERT INTO applications (id, student_id, job_id, resume_path, applied_at, status, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
    "events": "INSERT INTO events (id, company_id, event_name, description, event_date, event_time, location, eligibility, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
    "event_registrations": "INSERT INTO event_registrations (id, student_id, event_id, registered_at) VALUES (%s,%s,%s,%s)",
    "student_preferences": "INSERT INTO student_preferences (student_id, preferred_city, preferred_category, minimum_salary, preferred_work_mode, preferred_major, preferred_event_major, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
}


def load_rows(rows):
    connection = connect(DATABASE)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0]:
                raise SystemExit(
                    f"{DATABASE} already has data. Re-run with --reset to rebuild it."
                )
            for table, statement in INSERTS.items():
                cursor.executemany(statement, rows[table])
        connection.commit()
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="drop and recreate the database first")
    parser.add_argument("--anchor-date", type=date.fromisoformat, default=date.today(),
                        help="date that seeded dates are offsets from (default: today)")
    args = parser.parse_args()

    apply_schema(args.reset)
    rows = build_rows(args.anchor_date)
    load_rows(rows)

    print(f"Seeded {DATABASE} with SEED={SEED}, CITY_SET={CITY_SET}, anchor={args.anchor_date}")
    for table in INSERTS:
        print(f"  {table:<22}{len(rows[table]):>6}")
    print(f"Every seeded account uses the password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
