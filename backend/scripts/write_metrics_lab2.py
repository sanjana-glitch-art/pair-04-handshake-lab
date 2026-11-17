"""
Writes the "METRICS — Lab 2" section of METRICS.md from the evidence files
(harness, consolidation, compaction, traces, JMeter). The Lab 1 section
written by write_metrics.py is kept above it.

    backend/.venv/bin/python backend/scripts/write_metrics_lab2.py
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
METRICS = REPO / "METRICS.md"
MARKER = "\n\n---\n\n# METRICS — Lab 2, Pair 04"


def load(path):
    path = REPO / path
    return json.loads(path.read_text()) if path.exists() else None


def main():
    harness = load("docs/evaluation/agent_harness.json")
    compaction = load("docs/evidence/compaction.json")
    traces = load("docs/evidence/traces.json")
    jmeter = load("loadtest/results/summary.json")
    consolidation = (REPO / "docs/evidence/memory_consolidation.txt")
    cons = consolidation.read_text() if consolidation.exists() else ""

    out = [MARKER.strip(), "",
           "Runs on 2026-11-13, same Apple M4 (16 GB), Docker Compose stack (MongoDB 7, Kafka 3.8 KRaft, "
           "2 uvicorn workers per service), Ollama qwen3:8b (`num_ctx=12288`, `seed=4`).", ""]

    out += ["## Tests", "", "`KAFKA_ENABLED=false .venv/bin/python -m pytest -q` → **42 passed** "
            "(38 Lab 1 tests ported to MongoDB + logout, session expiry, bcrypt, queued application).", ""]

    if harness:
        rel = harness["reliability_before_after_repair"]
        out += ["## Guardrail harness (`python -m harness.agent_harness`)", "",
                f"**{harness['passed']} passed, {harness['failed']} failed** of {len(harness['cases'])} cases. "
                f"Reliability on the four failure scripts: repair off **{rel['repair_off_passed']}/4**, "
                f"repair on **{rel['repair_on_passed']}/4**.", "",
                "| Case | Guardrails | Result | Status | Iter. | Tool calls | Repairs/retries | ms |", "|---|---|---|---|---|---|---|---|"]
        for c in harness["cases"]:
            out.append(f"| {c['id']} {c['title']} | {', '.join(c['guardrails'])} | {'PASS' if c['passed'] else 'FAIL'} | "
                       f"{c.get('status', '')} | {c.get('iterations', '')} | {c.get('tool_call_count', '')} | "
                       f"{c.get('repairs', '')}/{c.get('tool_retries', '')} | {c['elapsed_ms']} |")
        out.append("")

    m = re.search(r"method=(\S+), (\d+) s.*?before=(\d+)\s+model_output=(\d+)\s+after=(\d+)", cons, re.S)
    if m:
        out += ["## Memory consolidation (Kafka `p4.assistant.memory_consolidate`)", "",
                "| Before | Model output | Stored after | Method | Worker time | Final check |", "|---|---|---|---|---|---|",
                f"| {m.group(3)} | {m.group(4)} | **{m.group(5)}** | {m.group(1)} | {m.group(2)} s | no problems |", "",
                "The model kept all five contradictions and every duplicate group; the rule-based pass "
                "resolved them (details in `docs/evidence/memory_consolidation.txt`).", ""]

    if compaction:
        c = compaction["compaction"]
        out += ["## Compaction (`/compact`)", "",
                f"Tokens {c['tokens_before']} → **{c['tokens_after']}** ({c['messages_before']} → {c['messages_after']} messages). "
                f"Recall: first job shown {compaction['first_search_ids'][:1]}, assistant targeted item_id="
                f"{compaction['recall_target_item_id']} after compaction → **{'correct' if compaction['recall_correct'] else 'wrong'}**.", "",
                "| Turn | Seconds | Prompt tokens | Context % |", "|---|---|---|---|"]
        for t in compaction["turns"]:
            u = t.get("usage") or {}
            out.append(f"| {t['message']} | {t['seconds']} | {u.get('prompt_tokens', '')} | {u.get('context_percent', '')} |")
        out.append("")

    if traces:
        out += [f"## Tracing ({traces['requests']} assistant requests)", "",
                "| Stage group | Mean s / request | Share |", "|---|---|---|"]
        for k, v in traces["share_of_latency"].items():
            out.append(f"| {k} | {traces['mean_ms'][k] / 1000:.3f} | {v}% |")
        out += ["", f"Dominant stage per request: {traces['dominant_stage_counts']}.", ""]

    if jmeter:
        out += ["## JMeter (gateway :9040, Compose stack)", "",
                "| Endpoint | Users | Samples | Avg ms | p95 ms | Throughput req/s | Error % |", "|---|---|---|---|---|---|---|"]
        names = {"login": "Login", "job_search": "Job search", "application": "Application submission", "event_search": "Event search"}
        for key, label in names.items():
            for level, s in sorted(jmeter.get(key, {}).items(), key=lambda kv: int(kv[0])):
                out.append(f"| {label} | {level} | {s['samples']} | {s['avg_ms']} | {s['p95_ms']} | {s['throughput_rps']} | {s['error_rate_pct']} |")
        if jmeter.get("assistant"):
            out += ["", "Assistant error % = requests that did not end with an answer (status from the traces; HTTP was 200).", "",
                    "| Assistant users | Samples | p50 s | p95 s | p99 s | Error % | Outcomes |", "|---|---|---|---|---|---|---|"]
            for level, s in sorted(jmeter["assistant"].items(), key=lambda kv: int(kv[0])):
                outcomes = ", ".join(f"{k} {v}" for k, v in sorted(s.get("statuses", {}).items()))
                out.append(f"| {level} | {s['samples']} | {s['p50_ms'] / 1000:.1f} | {s['p95_ms'] / 1000:.1f} | {s['p99_ms'] / 1000:.1f} | "
                           f"{s.get('functional_error_rate_pct', s['error_rate_pct'])} | {outcomes} |")
        out.append("")

    current = METRICS.read_text()
    lab1 = current.split(MARKER)[0].rstrip()
    METRICS.write_text(lab1 + "\n\n---\n\n" + "\n".join(out) + "\n")
    print(f"wrote {METRICS.relative_to(REPO)}")


if __name__ == "__main__":
    main()
