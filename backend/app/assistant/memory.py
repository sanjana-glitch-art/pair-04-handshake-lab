"""
Three-layer assistant memory.

Layer          Collection           Contents
-------------  -------------------  ------------------------------------------------
Instructions   assistant_rules      Rules the assistant always follows.
Learned        student_memory       One entry per fact: ISO date | category | description.
Session        assistant_sessions   The current conversation only; expires (TTL) or is
                                    compacted (compaction.py) and is discarded at the end.

Layers 1 and 2 are injected into the system prompt (prompt_block). The
memory worker (Kafka) learns new entries from each assistant request and
runs consolidation, so neither blocks a student's request.
"""

import json
import re
import time
from datetime import date

from pymongo.database import Database

from ..database import utcnow
from ..observability import log_event, record_stage


DEFAULT_RULES = [
    "Never reveal private information (email, phone, date of birth, applications) about any student other than the signed-in student.",
    "Always state an event's eligibility requirements when you recommend or describe an event.",
    "Always say whether pay is hourly or yearly.",
    "Only save a job or event after the student confirms; if they decline, do not save it.",
    "If learned memory disagrees with the student's saved preferences or a tool result, trust the preferences and tool result.",
]

CATEGORIES = ["preference", "goal", "skill", "location", "education", "constraint", "activity"]
MAX_PROMPT_ENTRIES = 40
TARGET_MAX_ENTRIES = 39  # "below 40" after consolidation


# ------------------------------------------------------------------ layer 1

def ensure_rules(db: Database) -> None:
    if db.assistant_rules.count_documents({}) == 0:
        db.assistant_rules.insert_many([
            {"_id": index, "order": index, "rule": rule, "created_at": utcnow()}
            for index, rule in enumerate(DEFAULT_RULES, start=1)
        ])


def get_rules(db: Database) -> list[str]:
    ensure_rules(db)
    return [doc["rule"] for doc in db.assistant_rules.find().sort("order", 1)]


# ------------------------------------------------------------------ layer 2

def format_entry(entry: dict) -> str:
    return f"{entry['date']} | {entry['category']} | {entry['description']}"


def get_memory(db: Database, student_id: int) -> list[dict]:
    return list(db.student_memory.find({"student_id": student_id}).sort([("date", 1), ("_id", 1)]))


def add_memory(db: Database, student_id: int, category: str, description: str,
               on: str | None = None, source: str = "student") -> bool:
    """
    Adds one entry unless the exact same fact is already stored.
    """

    category = category if category in CATEGORIES else "preference"
    description = " ".join(description.split())[:300]
    if not description:
        return False

    if db.student_memory.find_one({"student_id": student_id, "category": category,
                                   "description": {"$regex": f"^{re.escape(description)}$", "$options": "i"}}):
        return False

    db.student_memory.insert_one({
        "student_id": student_id,
        "date": on or date.today().isoformat(),
        "category": category,
        "description": description,
        "source": source,
        "created_at": utcnow(),
    })
    return True


def prompt_block(db: Database, student_id: int) -> str:
    """
    Text appended to the system prompt: rules, then learned memory.
    """

    rules = get_rules(db)
    entries = get_memory(db, student_id)[-MAX_PROMPT_ENTRIES:]

    block = "Standing rules (always follow):\n" + "\n".join(f"- {rule}" for rule in rules)

    if entries:
        block += (
            "\n\nWhat you remember about this student from earlier sessions "
            "(date | category | description; newer entries win, and saved preferences "
            "and tool results win over memory). Use it to personalize answers and suggestions, "
            "but do NOT turn it into search filters: only use filters the student asked for in "
            "this conversation or that come from get_student_preferences.\n"
            + "\n".join(format_entry(e) for e in entries)
        )

    return block


# ------------------------------------------------------- learning (worker)

LEARN_PATTERNS = [
    ("skill", re.compile(r"\b(?:i (?:know|use|am good at|have experience (?:with|in))|my skills (?:are|include))\s+(.+)", re.I)),
    ("education", re.compile(r"\b(i(?:'m| am) graduating .+|i graduate .+|my major is .+|i(?:'m| am) majoring in .+)", re.I)),
    ("location", re.compile(r"\b(i(?:'m| am) moving to .+|i live in .+|i(?:'m| am) based in .+|i(?:'m| am) relocating to .+)", re.I)),
    ("constraint", re.compile(r"\b(i (?:can(?:no|')t|cannot|don't|do not) .+|i(?:'m| am) not (?:interested|available) .+)", re.I)),
    ("goal", re.compile(r"\b(my goal is .+|i want to become .+|i(?:'m| am) aiming for .+)", re.I)),
    ("preference", re.compile(r"\b(i (?:prefer|like|want|would like|am interested in|'m interested in) .+)", re.I)),
]

SEARCH_WORDS = re.compile(r"\b(find|search|show|looking for|recommend|any)\b", re.I)


def extract_facts(user_message: str) -> list[tuple[str, str]]:
    """
    Turns first-person statements into memory entries. Requests such as
    "find remote internships" become one activity entry.
    """

    facts = []
    text = user_message.strip()

    for category, pattern in LEARN_PATTERNS:
        match = pattern.search(text)
        if match:
            fact = match.group(1).rstrip(" .!?")
            if category == "skill":
                fact = f"Knows {fact}"
            facts.append((category, fact[0].upper() + fact[1:]))
            break

    if not facts and SEARCH_WORDS.search(text) and not text.startswith("/"):
        facts.append(("activity", f"Asked the assistant: {text[:160]}"))

    return facts


def learn_from_interaction(db: Database, message: dict) -> str:
    payload = message["payload"]
    added = 0

    for category, fact in extract_facts(payload.get("user_message") or ""):
        added += add_memory(db, int(payload["student_id"]), category, fact, source="learned")

    log_event("memory learned", student_id=payload["student_id"], added=added)
    return "processed"


# --------------------------------------------------------- consolidation

def _norm(text: str) -> str:
    text = re.sub(r"[^a-z0-9$ ]+", " ", text.lower())
    return " ".join(word for word in text.split() if word not in {"the", "a", "an", "student", "to", "for", "in", "on"})


def _similar(a: str, b: str) -> bool:
    left, right = set(_norm(a).split()), set(_norm(b).split())
    if not left or not right:
        return False
    return _norm(a) == _norm(b) or len(left & right) / len(left | right) >= 0.75


# A "slot" is a fact that can only have one current value. Two entries
# for the same slot with different values contradict each other; the
# newer one wins.
SLOTS = {
    "work_mode": (
        {"preference", "constraint"},
        re.compile(r"\b(remote|on-?site|in[- ]person|hybrid)\b", re.I),
    ),
    "preferred_city": (
        {"location", "preference"},
        re.compile(r"\b(san jose|santa clara|milpitas|san francisco|oakland|sunnyvale|fremont)\b", re.I),
    ),
    "graduation": (
        {"education"},
        re.compile(r"\b(?:graduat\w*)\b.*?\b((?:may|june|december|spring|fall|winter)?\s*20\d\d)\b", re.I),
    ),
    "finance_interest": (
        {"preference", "constraint"},
        re.compile(r"\b(not interested in (?:finance|fintech|banking)|open to (?:finance|fintech|banking)|interested in (?:finance|fintech|banking))", re.I),
    ),
    "minimum_pay": (
        {"preference", "constraint"},
        re.compile(r"(?:at least|above|minimum|over)\s*\$(\d+)", re.I),
    ),
}


def slot_of(entry: dict) -> tuple[str, str] | None:
    for slot, (categories, pattern) in SLOTS.items():
        if entry["category"] in categories:
            match = pattern.search(entry["description"])
            if match:
                value = match.group(1).lower().replace("-", "").replace(" ", "")
                if slot == "work_mode":
                    value = {"inperson": "onsite"}.get(value, value)
                return slot, value
    return None


def deterministic_consolidation(entries: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Rule-based pass used to check (and, if needed, correct or replace)
    the model's consolidation:
    1. near-duplicates in the same category are merged (newest date kept);
    2. contradictions in a slot keep only the newest entry;
    3. single-skill entries are merged into one skills line;
    4. old activity entries are summarized, keeping the five newest.
    """

    decisions: list[str] = []
    entries = sorted(entries, key=lambda e: e["date"])
    kept: list[dict] = []

    for entry in entries:
        # Entries that hold different values of the same slot ($30 vs $35)
        # are a contradiction, not a duplicate, however similar the wording.
        twin = next(
            (k for k in kept
             if k["category"] == entry["category"]
             and _similar(k["description"], entry["description"])
             and slot_of(k) == slot_of(entry)),
            None,
        )
        if twin:
            decisions.append(f"duplicate merged: '{entry['description']}' = '{twin['description']}' (kept date {entry['date']})")
            twin["date"] = max(twin["date"], entry["date"])
            continue
        kept.append(dict(entry))

    latest_by_slot: dict[str, dict] = {}
    for entry in kept:
        slot = slot_of(entry)
        if slot:
            latest_by_slot[slot[0]] = entry  # sorted by date, so the last one is newest

    resolved = []
    for entry in kept:
        slot = slot_of(entry)
        if slot and latest_by_slot[slot[0]] is not entry:
            newer = latest_by_slot[slot[0]]
            decisions.append(
                f"contradiction ({slot[0]}): dropped {entry['date']} '{entry['description']}' "
                f"in favour of newer {newer['date']} '{newer['description']}'"
            )
            continue
        resolved.append(entry)

    skills = [e for e in resolved if e["category"] == "skill"]
    if len(skills) > 1:
        names = []
        for entry in skills:
            text = re.sub(r"^(knows|skill:|skilled in|uses)\s*", "", entry["description"], flags=re.I)
            for part in re.split(r",| and ", text):
                part = part.strip(" .")
                if part and part.lower() not in {n.lower() for n in names}:
                    names.append(part)
        merged = {"date": max(e["date"] for e in skills), "category": "skill", "description": "Knows " + ", ".join(names)}
        decisions.append(f"merged {len(skills)} skill entries into one: {merged['description']}")
        resolved = [e for e in resolved if e["category"] != "skill"] + [merged]

    activity = sorted([e for e in resolved if e["category"] == "activity"], key=lambda e: e["date"])
    if len(activity) > 5:
        older, newest = activity[:-5], activity[-5:]
        summary = {
            "date": older[-1]["date"],
            "category": "activity",
            "description": f"Earlier: {len(older)} searches between {older[0]['date']} and {older[-1]['date']} "
                           "(jobs, internships, and events).",
        }
        decisions.append(f"summarized {len(older)} older activity entries into one")
        resolved = [e for e in resolved if e["category"] != "activity"] + [summary] + newest

    return sorted(resolved, key=lambda e: (e["date"], e["category"])), decisions


CONSOLIDATION_PROMPT = """You maintain a career assistant's long-term memory about one student.
Consolidate the entries below. Rules:
- Merge duplicates and near-duplicates into one entry.
- When two entries contradict each other (for example remote vs onsite, two different cities,
  two graduation dates), keep only the NEWER entry by date.
- Merge many single skills into one "Knows ..." entry.
- Summarize old activity entries; keep recent ones.
- Keep every distinct, still-true fact. Never invent facts.
- Return fewer than 40 entries.
Answer with JSON only: {"entries": [{"date": "YYYY-MM-DD", "category": "...", "description": "..."}],
"decisions": ["one short line per merge or contradiction you resolved"]}
Allowed categories: preference, goal, skill, location, education, constraint, activity.

Entries (date | category | description):
"""


def _model_consolidation(entries: list[dict], client) -> tuple[list[dict], list[str]]:
    text = "\n".join(format_entry(e) for e in entries)
    raw = client.complete_text(
        [{"role": "user", "content": CONSOLIDATION_PROMPT + text}],
        json_mode=True,
    )
    data = json.loads(raw)
    output = []
    for item in data.get("entries", []):
        if not isinstance(item, dict) or not item.get("description"):
            continue
        output.append({
            "date": str(item.get("date") or entries[-1]["date"])[:10],
            "category": item.get("category") if item.get("category") in CATEGORIES else "preference",
            "description": " ".join(str(item["description"]).split())[:300],
        })
    return output, [str(d) for d in data.get("decisions", [])][:60]


def verify_consolidation(before: list[dict], after: list[dict]) -> list[str]:
    """
    Problems with a consolidated list: too many entries, duplicates left,
    contradictions left, or a contradiction resolved toward the OLDER value.
    """

    problems = []

    if len(after) >= 40:
        problems.append(f"{len(after)} entries left (must be below 40)")

    for i, first in enumerate(after):
        for second in after[i + 1:]:
            if (first["category"] == second["category"] and _similar(first["description"], second["description"])
                    and slot_of(first) == slot_of(second)):
                problems.append(f"duplicate left: '{first['description']}' / '{second['description']}'")

    newest_value: dict[str, tuple[str, str]] = {}
    for entry in sorted(before, key=lambda e: e["date"]):
        slot = slot_of(entry)
        if slot:
            newest_value[slot[0]] = (slot[1], entry["description"])

    for slot_name, (value, description) in newest_value.items():
        values = {slot[1] for slot in map(slot_of, after) if slot and slot[0] == slot_name}
        if len(values) > 1:
            problems.append(f"contradiction left in {slot_name}: {sorted(values)}")
        elif values and value not in values:
            problems.append(f"{slot_name} kept the older value {sorted(values)} instead of newest '{description}'")

    return problems


def consolidate_memory(db: Database, message: dict, client=None) -> str:
    """
    Kafka consumer for assistant.memory_consolidate. The model proposes a
    consolidated list; verify_consolidation checks it, and the rule-based
    pass corrects it when the model got something wrong.
    """

    student_id = int(message["payload"]["student_id"])
    before = [
        {"date": e["date"], "category": e["category"], "description": e["description"]}
        for e in get_memory(db, student_id)
    ]

    if len(before) < 2:
        return "processed"

    started = time.perf_counter()
    method, model_decisions, model_output, problems, corrections = "model", [], [], [], []

    try:
        if client is None:
            from .model_client import OllamaModelClient

            client = OllamaModelClient(timeout=float(message["payload"].get("timeout_s", 300)))
        model_output, model_decisions = _model_consolidation(before, client)
        problems = verify_consolidation(before, model_output)
    except Exception as error:  # noqa: BLE001 - model down or bad JSON: fall back
        problems = [f"model consolidation failed: {type(error).__name__}: {str(error)[:200]}"]

    record_stage("memory.consolidate.model", (time.perf_counter() - started) * 1000, message.get("trace_id"))

    if problems:
        # Correct the model's output with the rule-based pass when it is
        # usable, otherwise consolidate the original entries directly.
        base = model_output if model_output else before
        after, corrections = deterministic_consolidation(base)
        method = "model+rule_correction" if model_output else "rule_based_fallback"
        remaining = verify_consolidation(before, after)
        if remaining:
            after, corrections = deterministic_consolidation(before)
            method = "rule_based_fallback"
    else:
        after = sorted(model_output, key=lambda e: (e["date"], e["category"]))

    # The stored result must itself pass the checks; record what it shows.
    final_problems = verify_consolidation(before, after)

    db.memory_consolidations.insert_one({
        "student_id": student_id,
        "trace_id": message.get("trace_id"),
        "event_id": message.get("event_id"),
        "method": method,
        "before_count": len(before),
        "model_output_count": len(model_output),
        "after_count": len(after),
        "before": before,
        "model_output": model_output,
        "after": after,
        "model_decisions": model_decisions,
        "problems_found": problems,
        "corrections": corrections,
        "final_problems": final_problems,
        "ms": round((time.perf_counter() - started) * 1000, 1),
        "at": utcnow(),
    })

    db.student_memory.delete_many({"student_id": student_id})
    if after:
        db.student_memory.insert_many([
            {**entry, "student_id": student_id, "source": "consolidated", "created_at": utcnow()}
            for entry in after
        ])

    log_event("memory consolidated", student_id=student_id, before=len(before), after=len(after), method=method)
    return "processed"


# -------------------------------------------------------------- /memory

MEMORY_HELP = (
    "Memory commands:\n"
    "/memory - show what I remember about you\n"
    "/memory add <category>: <fact> - remember something (categories: " + ", ".join(CATEGORIES) + ")\n"
    "/memory consolidate - merge duplicates and resolve contradictions (runs in the background)\n"
    "/memory rules - show the rules I always follow\n"
    "/memory clear - forget everything I learned about you"
)


def handle_memory_command(db: Database, student_id: int, text: str, publish=None) -> str:
    parts = text.strip().split(maxsplit=1)
    argument = parts[1].strip() if len(parts) > 1 else ""

    if not argument or argument == "show":
        entries = get_memory(db, student_id)
        if not entries:
            return "I don't remember anything about you yet.\n\n" + MEMORY_HELP
        lines = "\n".join(f"{i}. {format_entry(e)}" for i, e in enumerate(entries, start=1))
        return f"I remember {len(entries)} thing(s) about you:\n{lines}"

    if argument == "rules":
        return "Rules I always follow:\n" + "\n".join(f"{i}. {r}" for i, r in enumerate(get_rules(db), start=1))

    if argument == "consolidate":
        count = db.student_memory.count_documents({"student_id": student_id})
        if publish is not None:
            publish(student_id)
        return (
            f"Consolidation of your {count} memory entries was queued. It runs in the background; "
            "type /memory in a minute to see the result."
        )

    if argument == "clear":
        removed = db.student_memory.delete_many({"student_id": student_id}).deleted_count
        return f"Forgot {removed} memory entries."

    if argument.startswith("add"):
        body = argument[3:].strip()
        category, _, fact = body.partition(":")
        if not fact:
            category, fact = "preference", body
        if add_memory(db, student_id, category.strip().lower(), fact.strip(), source="student"):
            return f"Remembered ({category.strip().lower() or 'preference'}): {fact.strip()}"
        return "I already remember that (or it was empty)."

    return MEMORY_HELP
