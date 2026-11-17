"""
Compaction evidence (Lab 2, Part 6) against the running stack and the real model.

    backend/.venv/bin/python backend/scripts/compaction_demo.py [--base http://localhost:9040/api]

1. two real turns that return jobs and events;
2. /compact: history replaced by the structured summary, tokens before/after;
3. recall check: "Save the first job you showed me" must target the same job id
   as the first search result (the save is then declined, so nothing changes).
Writes docs/evidence/compaction.json.
"""

import argparse
import json
import re
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:9040/api")
    # A seeded student with saved preferences and no learned memory, so the
    # run measures compaction rather than memory.
    parser.add_argument("--email", default="noprefs.student@example.edu")
    args = parser.parse_args()
    http = httpx.Client(base_url=args.base, timeout=900)

    token = http.post("/auth/login", json={"email": args.email, "password": "Pair4Demo!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    log, conversation_id = [], None

    def chat(message):
        nonlocal conversation_id
        started = time.time()
        body = http.post("/assistant/chat", json={"message": message, "conversation_id": conversation_id}, headers=headers).json()
        conversation_id = body["conversation_id"]
        entry = {"message": message, "seconds": round(time.time() - started, 1), "status": body["status"],
                 "usage": body.get("usage"), "compaction": body.get("compaction"), "trace_id": body.get("trace_id"),
                 "tool_calls": [{"name": c["name"], "arguments": c["arguments"]} for c in body["tool_calls"]],
                 "answer": body["answer"], "pending_action": body.get("pending_action")}
        log.append(entry)
        print(f"> {message}\n  [{entry['status']}, {entry['seconds']} s] usage={body.get('usage')}\n  {body['answer'][:300]}\n")
        return body, entry

    first, first_entry = chat("Find data science internships.")
    shown = [int(i) for c in first["tool_calls"] if c["name"] == "search_jobs" for i in re.findall(r"id=(\d+)", c["result"])]
    chat("Any career fairs or workshops next month?")
    compacted, _ = chat("/compact")
    recall, recall_entry = chat("Save the first job you showed me.")

    target = (recall.get("pending_action") or {}).get("arguments", {}).get("item_id")
    if recall.get("pending_action"):
        http.post("/assistant/confirm", json={"conversation_id": conversation_id, "approved": False}, headers=headers)

    result = {
        "student": args.email,
        "conversation_id": conversation_id,
        "first_search_ids": shown,
        "compaction": compacted.get("compaction"),
        "summary": compacted["answer"],
        "recall_target_item_id": target,
        "recall_correct": bool(shown) and target == shown[0],
        "turns": log,
    }
    out = REPO / "docs" / "evidence" / "compaction.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"first job shown: {shown[:1]}  -> after compaction the assistant targeted item_id={target}  correct={result['recall_correct']}")
    print(f"wrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
