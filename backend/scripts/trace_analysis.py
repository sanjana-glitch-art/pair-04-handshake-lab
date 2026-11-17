"""
Tracing evidence (Lab 2, Part 6).

    # send N assistant requests through the gateway, then analyse their traces
    backend/.venv/bin/python backend/scripts/trace_analysis.py --requests 50
    # analyse traces already stored (no new requests)
    backend/.venv/bin/python backend/scripts/trace_analysis.py --requests 0

Every assistant request gets a trace_id (X-Trace-Id) that is written on
each stage timing in the `traces` collection, carried in the Kafka
headers of assistant.interaction, and picked up by the memory worker
(kafka.queue_wait, worker.process). Stages are grouped into model
inference, database, tool execution (excluding its database time),
queue wait / Kafka, and other HTTP. Writes docs/evidence/traces.json and
docs/evidence/trace_latency.png.
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import get_database  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

PROMPTS = [
    "Find data science internships.",
    "Any career fairs next month?",
    "Find remote software internships.",
    "Show part-time jobs in Santa Clara.",
    "Find internships paying at least $40 an hour.",
    "Any events for Computer Science students?",
    "Find full-time data analyst jobs.",
    "Show on-campus jobs.",
    "Find machine learning internships in San Jose.",
    "Any resume workshops coming up?",
]


def category(stage: str) -> str:
    if stage.startswith("model."):
        return "model_inference"
    if stage.startswith("db."):
        return "database"
    if stage.startswith("tool."):
        return "tool_execution"
    if stage.startswith("kafka.") or stage.startswith("worker."):
        return "queue_and_worker"
    return "other"


def send(n: int, base: str, email: str) -> list[str]:
    http = httpx.Client(base_url=base, timeout=900)
    ids = []
    for i in range(n):
        # Sign in before every request: sessions expire after 60 minutes
        # and a long run (or a laptop that sleeps) would otherwise get 401s.
        token = http.post("/auth/login", json={"email": email, "password": "Pair4Demo!"}).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        prompt = PROMPTS[i % len(PROMPTS)]
        started = time.time()
        response = http.post("/assistant/chat", json={"message": prompt}, headers=headers)
        trace_id = response.headers.get("x-trace-id")
        ids.append(trace_id)
        status = response.json().get("status") if response.status_code == 200 else response.status_code
        print(f"{i + 1:>2}/{n} {status} {time.time() - started:6.1f}s trace={trace_id} {prompt}", flush=True)
        conversation = response.json().get("conversation_id") if response.status_code == 200 else None
        if conversation:
            http.delete(f"/assistant/conversations/{conversation}", headers=headers)
    return ids


def analyse(trace_ids: list[str] | None) -> dict:
    db = get_database()
    if not trace_ids:
        trace_ids = [t["trace_id"] for t in db.traces.find({"stage": "assistant.request"}).sort("started_at", -1).limit(50)]

    per_trace = []
    for trace_id in trace_ids:
        stages = list(db.traces.find({"trace_id": trace_id}).sort("started_at", 1))
        if not stages:
            continue
        totals = defaultdict(float)
        for s in stages:
            if s["stage"] != "assistant.request":
                totals[category(s["stage"])] += s["ms"]
        # tool.* timings include their own db.* time: report tool overhead separately.
        totals["tool_execution"] = max(0.0, totals["tool_execution"] - totals["database"])
        request = next((s for s in stages if s["stage"] == "assistant.request"), None)
        per_trace.append({
            "trace_id": trace_id,
            "ok": all(s["ok"] for s in stages),
            "request_ms": request["ms"] if request else None,
            "status": (request or {}).get("details", {}).get("status"),
            "breakdown_ms": {k: round(v, 1) for k, v in totals.items()},
            "dominant": max(totals, key=totals.get) if totals else None,
            "stages": [{"service": s["service"], "stage": s["stage"], "ms": s["ms"], "ok": s["ok"]} for s in stages],
        })

    summary = defaultdict(float)
    for t in per_trace:
        for k, v in t["breakdown_ms"].items():
            summary[k] += v
    total = sum(summary.values()) or 1
    dominant_counts = defaultdict(int)
    for t in per_trace:
        dominant_counts[t["dominant"]] += 1

    return {
        "requests": len(per_trace),
        "share_of_latency": {k: round(100 * v / total, 2) for k, v in sorted(summary.items(), key=lambda kv: -kv[1])},
        "mean_ms": {k: round(v / max(1, len(per_trace)), 1) for k, v in summary.items()},
        "dominant_stage_counts": dict(dominant_counts),
        "example_success": next((t for t in per_trace if t["ok"] and t["status"] == "final"), None),
        "example_failure": next((t for t in per_trace if not t["ok"]), None),
        "traces": per_trace,
    }


def plot(result: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = list(result["mean_ms"].keys())
    values = [result["mean_ms"][k] / 1000 for k in labels]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.barh(labels, values, color="#3b6ea5")
    ax.set_xlabel("mean seconds per assistant request")
    ax.set_title(f"Where assistant latency goes ({result['requests']} traced requests)")
    for i, v in enumerate(values):
        ax.text(v, i, f" {v:.2f}s", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--base", default="http://localhost:9040/api")
    parser.add_argument("--email", default="noprefs.student@example.edu")
    parser.add_argument("--also", nargs="*", default=[], help="earlier trace ids to include in the analysis")
    parser.add_argument("--fail-one", action="store_true",
                        help="also send one request to a temporary assistant container whose model address is "
                             "unreachable, to record a failed trace")
    args = parser.parse_args()

    ids = send(args.requests, args.base, args.email) if args.requests else None
    if args.fail_one:
        import subprocess

        name = "p4-assistant-failtest"
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        subprocess.run(["docker", "compose", "run", "-d", "--no-deps", "--name", name, "-p", "9056:9046",
                        "-e", "OLLAMA_HOST=http://host.docker.internal:1", "p4-assistant-service"],
                       cwd=REPO, check=True, capture_output=True)
        for _ in range(60):
            try:
                if httpx.get("http://localhost:9056/health", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(1)
        # Sign in through the gateway, then call the broken assistant directly.
        token = httpx.post(f"{args.base}/auth/login", json={"email": args.email, "password": "Pair4Demo!"}).json()["access_token"]
        response = httpx.post("http://localhost:9056/assistant/chat", json={"message": "Find data science internships."},
                              headers={"Authorization": f"Bearer {token}"}, timeout=120)
        print("failed-trace request:", response.status_code, response.json().get("status"), response.headers.get("x-trace-id"))
        ids = (ids or []) + [response.headers.get("x-trace-id")]
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    if args.also:
        ids = list(args.also) + (ids or [])
    time.sleep(3)  # let the memory worker record its queue-wait stages
    result = analyse(ids)

    out = REPO / "docs" / "evidence" / "traces.json"
    out.write_text(json.dumps(result, indent=2, default=str))
    try:
        plot(result, REPO / "docs" / "evidence" / "trace_latency.png")
    except ImportError:
        print("matplotlib not installed; skipped the chart")
    print(json.dumps({k: result[k] for k in ("requests", "share_of_latency", "mean_ms", "dominant_stage_counts")}, indent=2))


if __name__ == "__main__":
    main()
