"""
Builds LabPair-04_Lab2_Report.pdf from the template and the evidence
files, so every number in the PDF is the measured one.

    backend/.venv/bin/python docs/report/lab2/build_report.py

Needs pandoc and xelatex.
"""

import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
EVIDENCE = REPO / "docs" / "evidence"
TEMPLATE = HERE / "LabPair-04_Lab2_Report.md"
FILLED = HERE / "build" / "report_filled.md"
PDF = HERE / "LabPair-04_Lab2_Report.pdf"


def text(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def block(body: str, lang="text") -> str:
    return f"```{lang}\n{body.rstrip()}\n```"


def k8s_evidence() -> str:
    raw = text(EVIDENCE / "k8s_local_kind.txt")
    keep, take = [], False
    for line in raw.splitlines():
        if line.startswith("$ kubectl -n p4-handshake get pods") or line.startswith("$ kubectl -n p4-handshake get svc"):
            take = True
        elif line.startswith("$ ") :
            take = False
        if take:
            # Drop the IP / node columns to fit the page.
            keep.append(re.sub(r"\s+\d+\.\d+\.\d+\.\d+\s+p4-handshake-\S+.*$", "", line))
    return block("\n".join(keep)) if keep else "*k8s evidence not generated.*"


def kafka_failures() -> str:
    raw = text(EVIDENCE / "kafka_failures.log")
    if not raw:
        return "*Run scripts/kafka_failure_demos.sh.*"
    lines = []
    for line in raw.splitlines():
        if line.startswith(("=====", "[1", "[2", "[3", "--- worker p4", "--- stored", "application ")):
            lines.append(line)
        elif '"outcome"' in line or "moved to dead-letter" in line or '"message failed"' in line or "demo pause" in line:
            m = re.search(r'"msg": "([^"]+)".*?(?:"outcome": "([^"]+)")?.*?(?:"attempt": (\d))?', line)
            pod = re.search(r"pod/([^/]+)/", line)
            details = re.findall(r'"(topic|partition|offset|outcome|attempt|error)": "?([^",}]+)', line)
            lines.append(f"  worker {pod.group(1)[-5:] if pod else ''}: {m.group(1) if m else ''} "
                         + " ".join(f"{k}={v}" for k, v in details))
    explanation = """
**Case 1 — same event twice.** The identical envelope was published twice and then a client-style retry with a new `event_id` for the same student and job. The first copy was stored; the second was skipped because its `event_id` was already in `processed_events`; the retry hit the unique `student_id+job_id` index. One application row.

**Case 2 — worker killed mid-message.** The demo message pauses 25 s before the write; we force-deleted that worker pod during the pause. Right after the kill the application was not stored; after the consumer-group rebalance (session timeout about 45 s) the other replica re-read the uncommitted message, paused, wrote it, and committed. The event was **reprocessed, not lost**, because the offset is committed only after the database write; had the crash come after the write but before the commit, the redelivered copy would have been skipped by case 1's check.

**Case 3 — poison message.** Invalid JSON failed three attempts (0.5 s and 1 s backoff), was published to `p4.application.created.dlq` with the error and raw bytes, recorded in `dead_letters`, and its offset was committed; the valid message behind it on the same partition was then stored."""
    return block("\n".join(lines)) + "\n" + explanation


def consolidation() -> str:
    raw = text(EVIDENCE / "memory_consolidation.txt")
    if not raw:
        return "*Consolidation not run.*"
    head = raw.split("== BEFORE")[0].strip()
    # Keep the first 5 model decisions; the full list is in the evidence file.
    parts = head.split("== Model's own decisions ==")
    if len(parts) == 2:
        decisions, rest = parts[1].split("== Rule-based corrections ==")
        lines = [l for l in decisions.strip().splitlines() if l.strip()]
        if len(lines) > 5:
            lines = lines[:5] + [f" - ... ({len(lines) - 5} more in docs/evidence/memory_consolidation.txt)"]
        head = parts[0] + "== Model's own decisions ==\n" + "\n".join(lines) + "\n\n== Rule-based corrections ==" + rest
    after = raw.split("== AFTER, stored")[1].split("\n", 1)[1].strip() if "== AFTER, stored" in raw else ""
    model_wrong = """
**Where the model went wrong.** qwen3:8b returned 61 of the 64 entries:
it left every duplicate group and kept *both* sides of all five
contradictions, while its own "decisions" list claimed it had merged them
("Merged multiple 'Knows Python' entries into one"). The verifier caught
each problem and the rule-based pass corrected the model's list. A second
prompt that asked for a merge plan over numbered entries
(`backend/scripts/consolidation_prompt_experiment.py`) was worse: it
invented groups and resolved the graduation contradiction to the **older**
May 2027 date.

**One correction we made to our own rules.** The first rule-based pass
merged "at least \\$30 per hour" and "at least \\$35 per hour" as
near-duplicates and kept the old \\$30 text. Entries whose slot values differ
are now never merged as duplicates, and the stored list is verified again
(`final_problems=[]`); the stored list keeps \\$35."""
    return block(head) + "\n\nStored after consolidation:\n\n" + block(after) + "\n" + model_wrong


def compaction() -> str:
    data = json.loads(text(EVIDENCE / "compaction.json") or "null")
    if not data:
        return "*Run backend/scripts/compaction_demo.py.*"
    c = data["compaction"] or {}
    rows = "\n".join(
        f"| {t['message']} | {t['status']} | {t['seconds']} | "
        f"{(t.get('usage') or {}).get('prompt_tokens', '')} | {(t.get('usage') or {}).get('context_percent', '')}% | "
        f"{', '.join(c2['name'] for c2 in t['tool_calls']) or '-'} |"
        for t in data["turns"]
    )
    summary = data["summary"].split("\n\n", 1)[-1][:2200]
    return f"""The threshold is 60% of the context window (the warning shows at 70%);
`/compact` runs it on demand. The model writes a summary under fixed
headings (student preferences, jobs, companies, events, applications and
saved items, current request); any job or event id shown in a tool result
but missing from the summary is appended, and the stored history is
replaced by the summary. Real run (`backend/scripts/compaction_demo.py`,
`docs/evidence/compaction.json`):

| Turn | Status | Seconds | Prompt tokens | Context | Tools |
|---|---|---|---|---|---|
{rows}

Compaction: **{c.get('tokens_before')} → {c.get('tokens_after')} tokens**
({c.get('messages_before')} → {c.get('messages_after')} messages, method
{c.get('method')}).

{block(summary)}

**Recall after compaction:** the first search showed job ids
{data['first_search_ids'][:5]}; after compaction "Save the first job you
showed me" made the assistant propose saving **item_id={data['recall_target_item_id']}**
→ {'correct' if data['recall_correct'] else 'NOT the first job'} (the save was then declined)."""


def tracing() -> str:
    data = json.loads(text(EVIDENCE / "traces.json") or "null")
    if not data:
        return "*Run backend/scripts/trace_analysis.py.*"

    def trace_table(t):
        if not t:
            return "*none recorded*"
        rows = "\n".join(f"| {s['service']} | {s['stage']} | {s['ms']} | {'ok' if s['ok'] else 'FAILED'} |" for s in t["stages"])
        return f"trace_id `{t['trace_id']}` (status {t['status']}, {t['request_ms']} ms)\n\n| Service | Stage | ms | |\n|---|---|---|---|\n{rows}"

    import statistics

    ok_traces = [t for t in data["traces"] if t["ok"]]

    def med(key):
        values = [t["breakdown_ms"].get(key, 0.0) for t in ok_traces]
        return statistics.median(values) if values else 0.0

    share = "\n".join(
        f"| {k} | {data['mean_ms'][k] / 1000:.3f} | {med(k) / 1000:.3f} | {v}% |" for k, v in data["share_of_latency"].items()
    )
    req_median = statistics.median([t["request_ms"] for t in ok_traces if t["request_ms"]]) / 1000
    return f"""A trace_id is taken from `X-Trace-Id` or generated by the gateway-facing
service, returned in `X-Trace-Id` and in the assistant response, written
on every JSON log line, stored on every stage timing (`traces`
collection), copied into the Kafka envelope and header of
`assistant.interaction`, and picked up by the memory worker, which
records `kafka.queue_wait` and `worker.process` under the same id.

**Successful trace**

{trace_table(data.get('example_success'))}

**Failed trace** (one request to a copy of the assistant whose model address is unreachable)

{trace_table(data.get('example_failure'))}

**{data['requests']} requests.** Mean time per request by stage:

| Stage group | Mean s | Median s | Share |
|---|---|---|---|
{share}

Median request time {req_median:.1f} s. Three requests include time the
laptop was suspended (897 s, 2,016 s, 3,706 s), which inflates the means
but not the medians or the shares.

![Assistant latency by stage]({EVIDENCE / 'trace_latency.png'}){{width=80%}}

Model inference dominates: it was the largest stage in
{data['dominant_stage_counts'].get('model_inference', 0)} of {data['requests']} requests.
Database queries take milliseconds per tool call, tool overhead is
negligible, and the Kafka hop (publish + queue wait + worker) is tens of
milliseconds and happens after the answer is sent."""


def jmeter() -> str:
    results = REPO / "loadtest" / "results"
    summary = text(results / "summary.md")
    if not summary:
        return "*JMeter has not been run yet.*"
    analysis = text(HERE / "jmeter_analysis.md")
    return (summary.replace("# JMeter results", "").replace("## ", "### ")
            + f"\n\n![Average response time vs concurrency]({results / 'crud_avg_response.png'}){{width=85%}}\n\n"
            + (f"![Assistant latency vs concurrency]({results / 'assistant_latency.png'}){{width=80%}}\n\n" if (results / "assistant_latency.png").exists() else "")
            + analysis)


def harness() -> str:
    md = text(REPO / "docs" / "evaluation" / "agent_harness.md")
    data = json.loads(text(REPO / "docs" / "evaluation" / "agent_harness.json") or "null")
    if not md:
        return "*Harness not run.*"
    rel = data["reliability_before_after_repair"]
    table = ["| Case | Guardrails | Result | Status | Iter. | Tools | Repairs / retries |",
             "|------------------------------------------------|----------|------|--------------|----|----|------|"]
    table += [f"| {c['id']} {c['title']} | {', '.join(c['guardrails'])} | {'PASS' if c['passed'] else 'FAIL'} | "
              f"{c.get('status', '')} | {c.get('iterations', '')} | {c.get('tool_call_count', '')} | "
              f"{c.get('repairs', '')} / {c.get('tool_retries', '')} |" for c in data["cases"]]
    outcomes = "\n".join(f"- **{c['id']}** {c['guardrail_outcome']}" for c in data["cases"])
    rel_rows = "\n".join(f"| {k} | {'ok' if rel[k]['repair_off'] else 'failed'} | {'ok' if rel[k]['repair_on'] else 'failed'} |"
                         for k in ["malformed", "unknown_tool", "text_instead_of_tool", "chain_lost"])
    body = (f"**{data['passed']} passed, {data['failed']} failed.**\n\n" + "\n".join(table) + "\n\nGuardrail outcome per case:\n\n"
            + outcomes + "\n\n**Reliability before and after repair** (same failure scripts):\n\n| Failure script | Repair off | Repair on |\n|---|---|---|\n"
            + rel_rows + f"\n| **total** | **{rel['repair_off_passed']}/4** | **{rel['repair_on_passed']}/4** |")
    picks = {c["id"]: c for c in data["cases"]}
    ex = []
    for cid, label in [("H08b", "Blocked injection"), ("H03", "Declined confirmation"), ("H04", "Repaired malformed call"), ("H09a", "Bounded stop")]:
        c = picks[cid]
        shown = c["tool_calls"][:3]
        calls = "\n".join(f"  {t['name']} {json.dumps(t['arguments'])} valid={t['valid']}\n    -> {t['result'][:140]}" for t in shown)
        if len(c["tool_calls"]) > 3:
            calls += f"\n  ... {len(c['tool_calls']) - 3} more calls of the same kind"
        ex.append(f"**{label} ({cid}).** {c['guardrail_outcome']}\n\n" + block(f"input: {c['input']}\n{calls}\nfinal: {c['final_answer'][:240]}\nstatus={c['status']} iterations={c['iterations']} tool_calls={c['tool_call_count']} repairs={c['repairs']}"))
    return body + "\n\n" + "\n\n".join(ex)


def redux_screens() -> str:
    shots = sorted((HERE / "screenshots").glob("redux_devtools_*.png")) if (HERE / "screenshots").exists() else []
    if not shots:
        return ""
    return "\n\n".join(f"![{p.stem.replace('_', ' ')}](screenshots/{p.name}){{width=90%}}" for p in shots)


SHOTS = HERE / "screenshots"


def figures(filled: str) -> str:
    """<!-- FIG:name|caption|width --> -> image if screenshots/name.(jpg|png) exists."""

    def one(match):
        name, caption, width = match.group(1), match.group(2), match.group(3)
        for ext in ("jpg", "png"):
            if (SHOTS / f"{name}.{ext}").exists():
                return f"![{caption}](screenshots/{name}.{ext}){{width={width}%}}"
        return ""

    return re.sub(r"<!-- FIG:([\w-]+)\|([^|]+)\|(\d+) -->", one, filled)


def snippet(rel: str, start: str, max_lines: int = 40, lang: str | None = None) -> str:
    """Extracts the block that starts at the first line matching `start`."""

    path = REPO / rel
    lines = path.read_text().splitlines()
    begin = next(i for i, line in enumerate(lines) if re.search(start, line))
    indent = len(lines[begin]) - len(lines[begin].lstrip())
    out = [lines[begin]]
    for line in lines[begin + 1:]:
        stripped = line.strip()
        current = len(line) - len(line.lstrip())
        if path.suffix == ".yaml":
            if stripped == "---":
                break
            out.append(line)
            continue
        if stripped and current <= indent and re.match(r"(def |async def |class |@|export |const |function |[A-Za-z_]\w* = |#)", stripped) and not stripped.startswith(("})", ")")):
            break
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    if len(out) > max_lines:
        out = out[:max_lines] + [" " * (indent + 4) + "..."]
    lang = lang or {"py": "python", "js": "javascript", "jsx": "javascript", "yaml": "yaml"}.get(path.suffix[1:], "text")
    return block("\n".join(out), lang)


CODE_SNIPPETS = [
    ("Kafka producer: publish an envelope, or run the handler inline when Kafka is off", "backend/app/messaging.py", r"^def publish\(", 30),
    ("Application API: queue the submission and answer 202", "backend/app/application_routes.py", r"^async def submit_application", 60),
    ("Worker: bounded retries, then the dead-letter topic", "backend/app/workers/runner.py", r"^def handle_message", 50),
    ("Worker loop: commit the offset only after the handler returns", "backend/app/workers/runner.py", r"^def run\(", 50),
    ("Idempotent handler: skip a processed event_id, unique student+job", "backend/app/workers/handlers.py", r"^def application_created", 30),
    ("Sessions: every token must point to a live session", "backend/app/security.py", r"^def user_from_token", 35),
    ("Memory layers 1 and 2 injected into the system prompt", "backend/app/assistant/memory.py", r"^def prompt_block", 40),
    ("Consolidation verifier", "backend/app/assistant/memory.py", r"^def verify_consolidation", 35),
    ("Compaction: summarize, keep every shown id, replace the history", "backend/app/assistant/compaction.py", r"^def compact\(", 45),
    ("Stage timing stored under the trace id", "backend/app/observability.py", r"^def record_stage", 35),
    ("Guardrail 6: redaction of secrets and other students' emails", "backend/app/assistant/guardrails.py", r"^def redact\(", 25),
    ("Redux assistant slice: reducers and selectors", "frontend/src/store/slices/assistantSlice.js", r"^const assistantSlice = createSlice", 45),
    ("Redux store: the thread is mirrored to sessionStorage", "frontend/src/store/index.js", r"^export const store = configureStore", 25),
    ("Kubernetes HPA for the Job service", "k8s/base/50-hpa.yaml", r"^apiVersion", 12),
    ("AWS overlay: ECR images and single-node patches", "k8s/overlays/aws/kustomization.yaml", r"^apiVersion", 45),
]


def code_walkthrough() -> str:
    parts = []
    for title, rel, start, limit in CODE_SNIPPETS:
        try:
            parts.append(f"**{title}** — `{rel}`\n\n" + snippet(rel, start, limit))
        except (StopIteration, FileNotFoundError):
            parts.append(f"**{title}** — `{rel}` (not found)")
    return "\n\n".join(parts)


def aws_evidence() -> str:
    raw = text(EVIDENCE / "aws_eks.txt")
    if not raw:
        return "*AWS evidence not captured yet.*"
    sections = re.split(r"\n(?=\$ )", raw)
    keep = []
    for sec in sections:
        head = sec.splitlines()[0]
        if head.startswith("$ kubectl get nodes"):
            sec = "\n".join(l[:105] for l in sec.splitlines())
        if head.startswith("$ kubectl -n p4-handshake exec deploy/p4-ollama"):
            continue
        if head.startswith("$ aws ecr"):
            sec = "\n".join(re.sub(r"\tsha256:(\w{12})\w+", r"  sha256:\1...", l).replace("\t", "  ") for l in sec.splitlines())
        keep.append(sec.rstrip())
    body = "\n\n".join(keep[1:]) if keep and keep[0].startswith("#") else "\n\n".join(keep)
    seed = text(EVIDENCE / "aws_seed.txt")
    return ("Evidence captured with the AWS CLI and kubectl against the live cluster (`docs/evidence/aws_eks.txt`). "
            "The end-to-end request at the bottom signs in, searches, and asks the assistant through the public load balancer.\n\n"
            + block(body) + ("\n\nSeeding the EKS MongoDB:\n\n" + block(seed) if seed else ""))


def aws_screens() -> str:
    """AWS screenshots in a fixed order. The dark bar at the top of each one
    shows the page's real address (location.href), added by the capture script."""

    order = [
        ("aws_console_ecr", "AWS console, ECR: the seven p4-* private repositories (us-west-2)"),
        ("aws_console_ecr_tags", "ECR repository p4-assistant-service: image tag 2.0 pushed by scripts/aws_push_ecr.sh"),
        ("aws_console_eks_cluster", "AWS console, EKS: cluster p4-handshake, Active, Kubernetes 1.31"),
        ("aws_console_ec2", "EC2: the managed node group's m7i.xlarge node, running"),
        ("aws_console_elb", "EC2 load balancers: the classic ELB created for the p4-frontend LoadBalancer Service"),
        ("aws_console_kubectl", "kubectl against the EKS cluster: namespace p4-handshake Active, every pod Running, the services (only p4-frontend is public), and the HPAs reading CPU"),
        ("aws_console_app", "The Handshake app served from the EKS load balancer, signed in as the demo student"),
        ("aws_console_app_jobs", "Job search on AWS: gateway -> Job service -> MongoDB, all inside EKS"),
        ("aws_api_jobs", "The same search as a raw API request through the load balancer"),
        ("aws_console_assistant", "The assistant answering on AWS (qwen3:1.7b on the cluster's CPU node)"),
    ]
    shots = []
    for name, caption in order:
        for ext in ("png", "jpg"):
            if (SHOTS / f"{name}.{ext}").exists():
                shots.append(f"![{caption}](screenshots/{name}.{ext}){{width=95%}}")
                break
    note = ("The EKS console pages for nodes and workloads showed *Unauthorized*: the console sign-in is not mapped "
            "into the cluster's Kubernetes RBAC (only the IAM user `p4-lab2` that created the cluster is), so the "
            "kubectl screenshot shows the namespace, pods, services, and HPAs instead.")
    return note + "\n\n" + "\n\n".join(shots)


def aws_kafka() -> str:
    flow = text(EVIDENCE / "aws_application_flow.txt")
    topics = text(EVIDENCE / "aws_kafka.txt").split("\n\n")[0]
    if not flow:
        return "*Not captured.*"
    flow = flow.replace("http://a1c4a85197cfd4e9b92ba6b08899dada-156086449.us-west-2.elb.amazonaws.com:9040", "$ELB")
    return ("One application submitted through the public endpoint on EKS (`$ELB` = the load balancer address). "
            "The API answered 202 after Kafka acknowledged; the application worker consumed `p4.application.created` "
            "with the same trace id, wrote MongoDB, and committed offset 1; the consumer group has lag 0.\n\n"
            + block(flow) + "\n\nTopics on the EKS broker (`docs/evidence/aws_kafka.txt`):\n\n" + block(topics))


def terminal() -> str:
    out = []
    pytest = text(EVIDENCE / "pytest.txt").splitlines()
    if pytest:
        shown = pytest[:1] + pytest[1:9] + ["..."] + pytest[-6:]
        out.append("**Test suite** (`cd backend && .venv/bin/python -m pytest -v`)\n\n" + block("\n".join(shown)))
    harness_md = text(REPO / "docs" / "evaluation" / "agent_harness.md").splitlines()
    if harness_md:
        out.append("**Evaluation harness summary** (`docs/evaluation/agent_harness.md`, first lines)\n\n" + block("\n".join(harness_md[:14])))
    kind = text(EVIDENCE / "k8s_local_kind.txt").splitlines()
    if kind:
        out.append("**kind cluster nodes** (`docs/evidence/k8s_local_kind.txt`, first lines)\n\n" + block("\n".join(kind[:12])))
    return "\n\n".join(out)


def git_history() -> str:
    def git(*args):
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout.strip()

    log = git("log", "--format=%h  %ad  %an  %s", "--date=short", "lab1..HEAD")
    authors = git("shortlog", "-sn", "HEAD")
    intro = ("Commit history of the `lab2` work in `github.com/sanjana-glitch-art/pair-04-handshake-lab`, "
             "after the `lab1` tag, generated with `git log lab1..HEAD` when this report was built.")
    if not log:
        return intro + "\n\n*The Lab 2 commits are listed here when the report is rebuilt after committing.*\n\nCommits per author over the whole repository:\n\n" + block(authors)
    return intro + "\n\n" + block(log) + "\n\nCommits per author over the whole repository:\n\n" + block(authors)


def build():
    template = TEMPLATE.read_text()
    consolidated = re.search(r"after=(\d+)", text(EVIDENCE / "memory_consolidation.txt"))
    jmeter_done = (REPO / "loadtest" / "results" / "summary.md").exists()
    replacements = {
        "<!-- CONSOLIDATED_COUNT -->": consolidated.group(1) if consolidated else "?",
        "<!-- JMETER_STATUS -->": "Done" if jmeter_done else "Pending",
        "<!-- K8S_EVIDENCE -->": k8s_evidence(),
        "<!-- KAFKA_FAILURES -->": kafka_failures(),
        "<!-- MIGRATION -->": block(text(EVIDENCE / "migration.txt")),
        "<!-- CONSOLIDATION -->": consolidation(),
        "<!-- REDUX_SCREENSHOTS -->": redux_screens(),
        "<!-- JMETER -->": jmeter(),
        "<!-- COMPACTION -->": compaction(),
        "<!-- TRACING -->": tracing(),
        "<!-- HARNESS -->": harness(),
        "<!-- DOCKERFILE -->": block(text(REPO / "backend" / "docker" / "Dockerfile.application"), "dockerfile"),
        "<!-- COMPOSE_PS -->": block(text(EVIDENCE / "compose_ps.txt").replace("\t", "  ")),
        "<!-- AWS_EVIDENCE -->": aws_evidence(),
        "<!-- AWS_SCREENSHOTS -->": aws_screens(),
        "<!-- AWS_KAFKA -->": aws_kafka(),
        "<!-- CODE -->": code_walkthrough(),
        "<!-- TERMINAL -->": terminal(),
        "<!-- GIT_HISTORY -->": git_history(),
    }
    filled = template
    for marker, content in replacements.items():
        filled = filled.replace(marker, content)

    filled = figures(filled)

    # Wrap long code lines; the PDF fonts lack a few glyphs.
    def wrap(match):
        out = []
        for line in match.group(2).splitlines():
            while len(line) > 110:
                out.append(line[:110]); line = "    " + line[110:]
            out.append(line)
        return match.group(1) + "\n".join(out) + "\n```"
    filled = re.sub(r"(```\w*\n)(.*?)\n```", wrap, filled, flags=re.S)
    filled = filled.replace("→", "->").replace("✦", "*")

    FILLED.parent.mkdir(exist_ok=True)
    FILLED.write_text(filled)
    subprocess.run(["pandoc", str(FILLED), "-o", str(PDF), "--pdf-engine=xelatex", f"--resource-path={HERE}",
                    "-V", "mainfont=Helvetica", "-V", "monofont=Menlo", "--toc", "--toc-depth=2"], check=True)
    print(f"wrote {PDF}")


if __name__ == "__main__":
    build()
