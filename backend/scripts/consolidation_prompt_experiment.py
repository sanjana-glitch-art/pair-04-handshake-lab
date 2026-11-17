# Experiment (Lab 2 report): asks qwen3 for a merge plan over numbered memory entries
# instead of a rewritten list. Run from backend/: .venv/bin/python scripts/consolidation_prompt_experiment.py
import json, sys, time
sys.path.insert(0, '.'); sys.path.insert(0, '../database/seed')
from datetime import date, timedelta
from memory_fixture import ENTRIES, ACTIVITY
from app.assistant.model_client import OllamaModelClient
a = date(2026, 11, 13)
before = [{"date": (a-timedelta(days=d)).isoformat(), "category": c, "description": t} for d, c, t in ENTRIES] + \
         [{"date": (a-timedelta(days=85-3*i)).isoformat(), "category": "activity", "description": "Asked the assistant: "+t} for i, t in enumerate(ACTIVITY)]
before.sort(key=lambda e: e["date"])
lines = "\n".join(f"[{i}] {e['date']} | {e['category']} | {e['description']}" for i, e in enumerate(before))
prompt = """You clean up a career assistant's memory about one student. Entries are numbered.
Return JSON only:
{"groups": [{"ids": [numbers of entries that say the same thing or contradict each other],
             "keep": "one consolidated description (for a contradiction, the NEWEST entry's value)",
             "reason": "duplicate" | "contradiction" | "merge"}],
 "drop": [numbers of entries that are no longer useful]}
Rules: group exact or near duplicates; group contradictions (remote vs onsite, two cities, two graduation
dates, two pay minimums, finance yes/no) and keep the NEWER value; merge all single skills into one group;
merge activity entries older than the newest five into one group. Entries not mentioned are kept as they are.

Entries:
""" + lines
c = OllamaModelClient(timeout=600)
t = time.time()
raw = c.complete_text([{"role": "user", "content": prompt}], json_mode=True)
print(round(time.time()-t), "s"); print(raw[:3000])
