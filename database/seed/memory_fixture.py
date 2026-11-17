"""
Memory fixture for the consolidation demo (Lab 2, Part 3).

Gives the demo student 64 learned-memory entries, including
- 5 deliberate contradictions (work mode, city, graduation date,
  finance interest, minimum pay); the newer entry is the true one;
- 3 duplicate groups (7 entries) written slightly differently;
- 11 single-skill entries (one of them a duplicate) and 25 activity
  entries that consolidation should merge or summarize.

    backend/.venv/bin/python database/seed/memory_fixture.py   # reload only the fixture
"""

import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.assistant.memory import ensure_rules  # noqa: E402
from app.database import get_database, utcnow  # noqa: E402


DEMO_EMAIL = "demo.student@example.edu"

# (days before the anchor date, category, description)
ENTRIES = [
    # contradictions: old value ... newer value
    (80, "preference", "Prefers remote internships"),
    (12, "preference", "Now wants onsite roles only; no longer interested in remote work"),
    (75, "location", "Prefers jobs in San Jose"),
    (9, "location", "Moving to Milpitas next month; prefers jobs in Milpitas"),
    (70, "education", "Graduating in May 2027"),
    (15, "education", "Graduation moved earlier to December 2026"),
    (60, "preference", "Not interested in finance or fintech companies"),
    (6, "preference", "Now open to fintech companies after the Golden Gate Fintech info session"),
    (50, "preference", "Wants internships paying at least $30 per hour"),
    (5, "preference", "Wants internships paying at least $35 per hour"),
    # duplicates
    (65, "preference", "Interested in data science internships"),
    (40, "preference", "Interested in data science internships."),
    (20, "preference", "interested in Data Science internships"),
    (55, "goal", "Wants to become a machine learning engineer"),
    (30, "goal", "Wants to become a Machine Learning Engineer"),
    (45, "constraint", "Cannot work more than 20 hours a week during the semester"),
    (25, "constraint", "Cannot work more than 20 hours per week during the semester"),
    # single skills (Python twice)
    (90, "skill", "Knows Python"),
    (89, "skill", "Knows SQL"),
    (88, "skill", "Knows Pandas"),
    (72, "skill", "Knows Tableau"),
    (68, "skill", "Knows Machine Learning"),
    (58, "skill", "Knows Statistics"),
    (49, "skill", "Knows Git"),
    (38, "skill", "Knows Docker"),
    (27, "skill", "Knows Spark"),
    (16, "skill", "Knows R"),
    (8, "skill", "Knows python"),
    # other still-true facts
    (90, "education", "Majoring in Data Science at San Jose State University"),
    (86, "education", "Current CGPA is 3.6"),
    (35, "goal", "Wants a summer 2027 internship"),
    (28, "goal", "Plans to apply to at least five jobs per week"),
    (33, "constraint", "Needs visa sponsorship information before applying"),
    (18, "constraint", "Has no car; needs jobs near public transit"),
    (52, "preference", "Likes companies with mentorship programs"),
    (47, "preference", "Prefers small and mid-size companies"),
    (22, "preference", "Interested in career fairs and resume workshops"),
    (14, "preference", "Prefers events after 4 PM because of classes"),
    (11, "preference", "Wants to save interesting jobs to review later"),
]

ACTIVITY = [
    "find remote data science internships", "show data analyst jobs in San Jose",
    "any career fairs next month", "find internships paying over $30 an hour",
    "show me machine learning internships", "search events for Computer Science students",
    "find Python jobs near me", "show jobs at TechNova Solutions", "recommend resume workshops",
    "find part-time on-campus jobs", "show data engineering internships", "any AI meetups this month",
    "find SQL internships in Santa Clara", "show me higher paying data science internships",
    "find jobs with Tableau", "search events in Milpitas", "show internships closing this week",
    "find fintech internships", "find onsite internships in Milpitas", "any networking events after 4 PM",
    "show Spark data engineering roles", "find internships with mentorship", "search hackathons",
    "show me jobs I saved", "find data science internships paying at least $35",
]


def seed_memory(db=None, anchor: date | None = None) -> int:
    db = db if db is not None else get_database()
    anchor = anchor or date.today()
    ensure_rules(db)

    user = db.users.find_one({"email": DEMO_EMAIL})
    if user is None:
        raise SystemExit(f"{DEMO_EMAIL} is not in the database; run generate_seed.py first.")

    entries = [
        {"date": (anchor - timedelta(days=days)).isoformat(), "category": category, "description": text}
        for days, category, text in ENTRIES
    ] + [
        {"date": (anchor - timedelta(days=85 - 3 * i)).isoformat(), "category": "activity",
         "description": f"Asked the assistant: {text}"}
        for i, text in enumerate(ACTIVITY)
    ]

    db.student_memory.delete_many({"student_id": user["_id"]})
    db.student_memory.insert_many([
        {**entry, "student_id": user["_id"], "source": "fixture", "created_at": utcnow()}
        for entry in entries
    ])
    return len(entries)


if __name__ == "__main__":
    print(f"Loaded {seed_memory()} memory entries for {DEMO_EMAIL}")
