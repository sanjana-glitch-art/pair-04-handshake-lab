"""
Summarizes loadtest/results/*.jtl into loadtest/results/summary.json,
loadtest/results/summary.md, and two graphs:
  crud_avg_response.png       average response time vs concurrency (4 CRUD endpoints)
  assistant_latency.png       p50/p95/p99 vs concurrency for the assistant

    backend/.venv/bin/python loadtest/analyze_results.py
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
GAP_MS = 30_000

LABELS = {
    "login": "Login",
    "job_search": "Job search",
    "application": "Application submission",
    "event_search": "Event search",
    "assistant": "Assistant chat",
}


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return round(values[lo] + (values[hi] - values[lo]) * (k - lo), 1)


def load(path: Path, label: str):
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row["label"] == label:
                rows.append(row)
    return rows


def summarize(rows):
    elapsed = [int(r["elapsed"]) for r in rows]
    starts = [int(r["timeStamp"]) for r in rows]
    ends = [int(r["timeStamp"]) + int(r["elapsed"]) for r in rows]
    errors = [r for r in rows if r["success"] != "true"]
    # Active time only: the laptop running the test suspended a few times
    # (gaps of 700-1,060 s with no request in flight). Idle gaps longer than
    # GAP_MS are removed so throughput reflects the time requests were running.
    spans = sorted(zip(starts, ends))
    active, cur_start, cur_end, gaps_removed = 0, spans[0][0], spans[0][1], 0
    for start, end in spans[1:]:
        if start - cur_end > GAP_MS:
            active += cur_end - cur_start
            cur_start, gaps_removed = start, gaps_removed + 1
        cur_end = max(cur_end, end)
    active += cur_end - cur_start
    duration = max(1, active) / 1000
    codes = defaultdict(int)
    for r in errors:
        codes[r["responseCode"]] += 1
    return {
        "samples": len(rows),
        "avg_ms": round(sum(elapsed) / len(elapsed), 1),
        "p50_ms": percentile(elapsed, 50),
        "p95_ms": percentile(elapsed, 95),
        "p99_ms": percentile(elapsed, 99),
        "max_ms": max(elapsed),
        "throughput_rps": round(len(rows) / duration, 2),
        "error_rate_pct": round(100 * len(errors) / len(rows), 2),
        "error_codes": dict(codes),
        "active_seconds": round(duration, 1),
        "idle_gaps_removed": gaps_removed,
    }


def assistant_statuses(level: int, rows) -> dict | None:
    """
    The assistant answers HTTP 200 even when the model failed, so the
    runs before the JSON assertion was added report 0% errors. The real
    outcome of each request is in the traces collection
    (stage assistant.request, details.status), recorded when the request
    ends; match them to the JMeter run by time window.
    """

    try:
        import sys
        from datetime import datetime, timedelta, timezone

        sys.path.insert(0, str(HERE.parent / "backend"))
        from app.database import get_database

        start = datetime.fromtimestamp(min(int(r["timeStamp"]) for r in rows) / 1000, timezone.utc).replace(tzinfo=None)
        end = datetime.fromtimestamp(max(int(r["timeStamp"]) + int(r["elapsed"]) for r in rows) / 1000, timezone.utc).replace(tzinfo=None)
        docs = list(get_database().traces.find({
            "stage": "assistant.request",
            "service": "assistant",
            "started_at": {"$gte": start, "$lte": end + timedelta(seconds=10)},
        }))
    except Exception:
        return None

    counts = defaultdict(int)
    for d in docs:
        counts[(d.get("details") or {}).get("status", "unknown")] += 1
    answered = counts.get("final", 0) + counts.get("confirmation_required", 0)
    return {"statuses": dict(counts), "traced": len(docs),
            "functional_error_rate_pct": round(100 * (len(rows) - answered) / len(rows), 1)}


def main():
    summary = defaultdict(dict)
    for path in sorted(RESULTS.glob("*.jtl")):
        match = re.match(r"(.+)_(\d+)\.jtl$", path.name)
        if not match:
            continue
        name, level = match.group(1), int(match.group(2))
        rows = load(path, LABELS[name])
        if rows:
            summary[name][level] = summarize(rows)
            if name == "assistant":
                status = assistant_statuses(level, rows)
                if status:
                    summary[name][level].update(status)

    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2))

    lines = ["# JMeter results", ""]
    lines += ["## CRUD endpoints", "", "| Endpoint | Users | Samples | Avg ms | p95 ms | Throughput req/s | Error % |", "|---|---|---|---|---|---|---|"]
    for name in ["login", "job_search", "application", "event_search"]:
        for level, s in sorted(summary.get(name, {}).items()):
            lines.append(f"| {LABELS[name]} | {level} | {s['samples']} | {s['avg_ms']} | {s['p95_ms']} | {s['throughput_rps']} | {s['error_rate_pct']} |")
    lines += ["", "## Assistant", "",
              "Error % counts every request that did not end with an answer (status `final`), taken from the traces; "
              "HTTP-level errors were 0% because the API returns 200 with status `model_error` or `timeout`.", "",
              "| Users | Samples | p50 s | p95 s | p99 s | Avg s | Error % | Outcomes |", "|---|---|---|---|---|---|---|---|"]
    for level, s in sorted(summary.get("assistant", {}).items()):
        err = s.get("functional_error_rate_pct", s["error_rate_pct"])
        outcomes = ", ".join(f"{k} {v}" for k, v in sorted(s.get("statuses", {}).items())) or s["error_codes"] or ""
        if "traced" in s and s["traced"] < s["samples"]:
            outcomes += f", no trace {s['samples'] - s['traced']} (laptop suspended; counted as errors)"
        lines.append(f"| {level} | {s['samples']} | {s['p50_ms'] / 1000:.1f} | {s['p95_ms'] / 1000:.1f} | {s['p99_ms'] / 1000:.1f} | "
                     f"{s['avg_ms'] / 1000:.1f} | {err} | {outcomes} |")
    (RESULTS / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4))
    for name, marker in [("login", "o"), ("job_search", "s"), ("application", "^"), ("event_search", "D")]:
        points = sorted(summary.get(name, {}).items())
        if points:
            ax.plot([p[0] for p in points], [p[1]["avg_ms"] for p in points], marker=marker, label=LABELS[name])
    ax.set_xlabel("concurrent users")
    ax.set_ylabel("average response time (ms)")
    ax.set_title("Average response time vs concurrency")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS / "crud_avg_response.png", dpi=160)

    points = sorted(summary.get("assistant", {}).items())
    if points:
        fig, ax = plt.subplots(figsize=(7, 4))
        for key, label in [("p50_ms", "p50"), ("p95_ms", "p95"), ("p99_ms", "p99"), ("avg_ms", "average")]:
            ax.plot([p[0] for p in points], [p[1][key] / 1000 for p in points], marker="o", label=label)
        ax.set_xlabel("concurrent users")
        ax.set_ylabel("latency (s)")
        ax.set_title("Assistant chat latency vs concurrency")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(RESULTS / "assistant_latency.png", dpi=160)


if __name__ == "__main__":
    main()
