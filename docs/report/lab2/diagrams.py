"""
Draws the Lab 2 architecture and Kafka flow diagrams (PNG) for the report.
    backend/.venv/bin/python docs/report/lab2/diagrams.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent

COLORS = {"web": "#dbe9f7", "api": "#e3f1e0", "data": "#fbe8cf", "kafka": "#f3dce6", "worker": "#ece4f5", "model": "#eeeeee"}


def box(ax, x, y, w, h, text, kind, size=8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=COLORS[kind], ec="#555555", lw=0.9))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size)
    return (x, y, w, h)


def arrow(ax, a, b, text="", style="-|>", color="#444444", ls="-", rad=0.0, size=6.5, start="b", end="t"):
    def anchor(r, side):
        x, y, w, h = r
        return {"t": (x + w / 2, y + h), "b": (x + w / 2, y), "l": (x, y + h / 2), "r": (x + w, y + h / 2)}[side]
    p1, p2 = anchor(a, start), anchor(b, end)
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=9, color=color, lw=0.9, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, text, fontsize=size, ha="center", va="center",
                bbox=dict(fc="white", ec="none", pad=0.6))


def architecture():
    fig, ax = plt.subplots(figsize=(11, 7.2))
    ax.set_xlim(0, 22); ax.set_ylim(0, 14.4); ax.axis("off")
    ax.text(11, 14.0, "Pair 4 Handshake - Lab 2 architecture (namespace p4-handshake)", ha="center", fontsize=11, weight="bold")

    browser = box(ax, 8.5, 12.4, 5, 0.9, "Browser (React + Redux)", "web", 9)
    gateway = box(ax, 7, 10.6, 8, 1.1, "p4-frontend: nginx + React build\nAPI gateway  /api/*  :9040  (LoadBalancer)", "web")
    arrow(ax, browser, gateway, "HTTP")

    names = [("student", "auth, sessions,\nprofiles, prefs,\nsaved, pictures", 9041),
             ("company", "company signup,\nprofile", 9042),
             ("job", "search,\npostings", 9043),
             ("application", "apply, withdraw,\ncompany review", 9044),
             ("event", "events,\nregistration", 9045),
             ("assistant", "agent loop, memory,\ncompaction, tokens", 9046)]
    services = {}
    for i, (n, d, port) in enumerate(names):
        services[n] = box(ax, 0.4 + i * 3.6, 7.6, 3.3, 1.9, f"p4-{n}-service\n:{port}\n{d}", "api", 7)
        arrow(ax, gateway, services[n], "", start="b", end="t")

    mongo = box(ax, 0.4, 4.4, 9.8, 1.6, "MongoDB p4_handshake (StatefulSet + PVC)\nusers, profiles, jobs, applications, events,\nsessions (TTL), activity_logs, assistant_rules, student_memory,\nassistant_sessions, traces, GridFS (resumes, pictures)", "data", 7)
    kafka = box(ax, 11.2, 4.4, 10.4, 1.6, "Kafka (KRaft StatefulSet), topics p4.* (3 partitions) + <topic>.dlq\napplication.created / updated / status_changed,\nevent.registration_created, job.created,\nassistant.interaction, assistant.memory_consolidate", "kafka", 7)

    for n in ["student", "company", "job"]:
        arrow(ax, services[n], mongo, "", color="#8a6d3b")
    arrow(ax, services["application"], mongo, "", color="#8a6d3b", rad=0.1)
    for n in ["job", "application", "event", "assistant"]:
        arrow(ax, services[n], kafka, "publish", color="#9c2f6b")

    workers = [("application worker", "writes applications"), ("notification worker", "status-change notes"),
               ("event worker", "writes registrations"), ("job worker", "search-term index"), ("memory worker", "learn + consolidate")]
    wboxes = []
    for i, (n, d) in enumerate(workers):
        wboxes.append(box(ax, 0.4 + i * 4.3, 1.6, 4.0, 1.2, f"p4-{n}\n{d}", "worker", 7.5))
        arrow(ax, kafka, wboxes[-1], "consume", color="#9c2f6b", start="b", end="t")
        arrow(ax, wboxes[-1], mongo, "", color="#8a6d3b", ls="--", start="t", end="b")

    ollama = box(ax, 18.3, 10.6, 3.4, 1.1, "Ollama qwen3:8b\n(host locally; pod on EKS)", "model", 7.5)
    arrow(ax, services["assistant"], ollama, "ModelClient", start="t", end="b")
    arrow(ax, services["assistant"], services["student"], "save via HTTP (student token)", color="#2e6b2e", rad=0.25, start="b", end="b", size=6.5)

    ax.text(0.4, 0.5, "Service discovery: <name>.p4-handshake.svc.cluster.local (Kubernetes) or the container name (Compose).\n"
            "Secrets from the p4-secrets Secret; settings from the p4-config ConfigMap.  trace_id: X-Trace-Id header -> Kafka header -> worker logs.",
            fontsize=7, color="#333333")
    fig.subplots_adjust(0.01, 0.01, 0.99, 0.99)
    fig.savefig(HERE / "architecture.png", dpi=170)


def kafka_flow():
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.set_xlim(0, 22); ax.set_ylim(0, 8.4); ax.axis("off")
    ax.text(11, 8.0, "Application submission through Kafka (idempotent, commit after write, DLQ)", ha="center", fontsize=10.5, weight="bold")
    s = box(ax, 0.3, 5.2, 3.6, 1.6, "Student\nPOST /api/applications\n(resume PDF)", "web")
    api = box(ax, 4.9, 5.2, 4.4, 1.6, "Application API\nvalidate, store resume (GridFS),\nallocate id -> publish -> 202", "api")
    topic = box(ax, 10.3, 5.2, 4.2, 1.6, "p4.application.created\nkey = student:job\nenvelope: event_id, trace_id", "kafka")
    w = box(ax, 15.5, 5.2, 6.2, 1.6, "application worker\n1 skip if event_id processed\n2 insert (unique _id, student+job)\n3 mark processed  4 commit offset", "worker", 7.5)
    db = box(ax, 15.5, 2.3, 6.2, 1.3, "MongoDB applications\n+ processed_events", "data")
    dlq = box(ax, 10.3, 2.3, 4.2, 1.3, "p4.application.created.dlq\n+ dead_letters collection", "kafka")
    arrow(ax, s, api, "", start="r", end="l")
    arrow(ax, api, topic, "produce (acks=all,\nidempotent)", start="r", end="l")
    arrow(ax, topic, w, "poll", start="r", end="l")
    arrow(ax, w, db, "write", start="b", end="t")
    arrow(ax, w, dlq, "after 3 failed attempts\n(0.5 s, 1 s backoff)", start="b", end="r", rad=-0.2, color="#9c2f6b")
    ax.text(0.3, 1.2, "Crash before step 4: the offset is not committed, so the message is redelivered after the group rebalance; step 1 / the unique "
            "keys make the re-run harmless.\nSame event published twice: skipped at step 1.  Same student+job with a new event_id: unique index -> duplicate_skipped.",
            fontsize=7.5, color="#333333")
    fig.subplots_adjust(0.01, 0.01, 0.99, 0.99)
    fig.savefig(HERE / "kafka_flow.png", dpi=170)


if __name__ == "__main__":
    architecture()
    kafka_flow()
    print("wrote architecture.png and kafka_flow.png")
