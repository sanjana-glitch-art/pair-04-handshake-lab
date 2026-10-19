"""
Re-scores a reliability run with argument checks and rewrites its
markdown report.

evaluate.py classifies the four failure modes the lab names. A call can
also be well-formed but wrong, e.g. category="internship" when the
student asked for part-time jobs. This script checks each turn's
arguments against what the prompt asked for, so "well-formed and
correct" means both.

    backend/.venv/bin/python backend/scripts/score_reliability.py
    backend/.venv/bin/python backend/scripts/score_reliability.py --tag nothink

If the JSON has no stored arguments (older runs), they are recovered from
the [tool] lines in docs/evaluation/console_log<tag>.txt.
"""

import argparse
import json
import re
from collections import Counter
from datetime import date, timedelta

from _common import REPO_ROOT

OUT_DIR = REPO_ROOT / "docs" / "evaluation"


def next_month(today):
    start = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return start, end


def lower(value):
    return str(value or "").lower()


def first(calls, name):
    return [c["arguments"] or {} for c in calls if c["name"] == name and c["valid"]]


def any_call(calls, name, predicate):
    return any(predicate(a) for a in first(calls, name))


def in_next_month(a, today, end_limit=None):
    start, end = next_month(today)
    try:
        return date.fromisoformat(a["date_from"]) >= start and date.fromisoformat(a["date_to"]) <= (end_limit or end)
    except (KeyError, ValueError, TypeError):
        return False


def checks(today):
    start, _ = next_month(today)
    mid = start + timedelta(days=14)

    return {
        "Find an internship in my city.":
            lambda c: any_call(c, "search_jobs", lambda a: "san jose" in lower(a.get("city")) and a.get("category") == "internship"),
        "Make it higher paying.":
            lambda c: any_call(c, "search_jobs", lambda a: a.get("sort_by") == "salary_desc" or (a.get("min_salary") or 0) > 25),
        "Tell me more about the first one.":
            lambda c: bool(first(c, "get_job_details")),
        "Find a remote data science internship that matches my Python and SQL skills.":
            lambda c: any_call(c, "search_jobs", lambda a: a.get("remote") is True and "data" in lower(a.get("title")) and a.get("skills")),
        "What are the details of job 4?":
            lambda c: any_call(c, "get_job_details", lambda a: a.get("job_id") == 4),
        "Show details for job 999999.":
            lambda c: any_call(c, "get_job_details", lambda a: a.get("job_id") == 999999),
        "Find an event for computer science students next month.":
            lambda c: any_call(c, "search_events", lambda a: in_next_month(a, today) and ("computer science" in lower(a.get("major")) or a.get("eligible_only"))),
        "Any career fairs in Santa Clara?":
            lambda c: any_call(c, "search_events", lambda a: "santa clara" in lower(a.get("city"))),
        "Are there any events for Finance students?":
            lambda c: any_call(c, "search_events", lambda a: "finance" in lower(a.get("major")) + lower(a.get("name"))),
        "Find me a marine biology job at SpaceX.":
            lambda c: any_call(c, "search_jobs", lambda a: "spacex" in lower(a.get("company")) or "marine" in lower(a.get("title"))),
        "Find full-time data engineer jobs paying at least 120000 a year.":
            lambda c: any_call(c, "search_jobs", lambda a: a.get("category") == "full_time" and (a.get("min_salary") or 0) >= 120000 and "engineer" in lower(a.get("title"))),
        "Find on-campus jobs in San Jose.":
            lambda c: any_call(c, "search_jobs", lambda a: a.get("category") == "on_campus" and "san jose" in lower(a.get("city"))),
        "Find part-time jobs that need customer service skills.":
            lambda c: any_call(c, "search_jobs", lambda a: a.get("category") == "part_time" and "customer service" in lower(a.get("skills"))),
        "Which jobs at TechNova Solutions are open?":
            lambda c: any_call(c, "search_jobs", lambda a: "technova" in lower(a.get("company"))),
        "What are my saved preferences?":
            lambda c: bool(first(c, "get_student_preferences")),
        "Find jobs that match my preferences.":
            lambda c: bool(first(c, "get_student_preferences")) and any_call(c, "search_jobs", lambda a: "san jose" in lower(a.get("city"))),
        "Find internships with deadlines after 2026-12-01.":
            lambda c: any_call(c, "search_jobs", lambda a: a.get("deadline_after") == "2026-12-01" and a.get("category") == "internship"),
        "Use the find_internships tool to get internships in Milpitas.":
            lambda c: any_call(c, "search_jobs", lambda a: a.get("category") == "internship" and "milpitas" in lower(a.get("city"))),
        "Get job details for job number twelve.":
            lambda c: any_call(c, "get_job_details", lambda a: a.get("job_id") == 12),
        "Find machine learning internships paying more than $40 an hour in Santa Clara.":
            lambda c: any_call(c, "search_jobs", lambda a: a.get("category") == "internship" and "santa clara" in lower(a.get("city")) and (a.get("min_salary") or 0) >= 40 and "machine" in lower(a.get("title"))),
        "Search for events in Milpitas during the first half of next month.":
            lambda c: any_call(c, "search_events", lambda a: "milpitas" in lower(a.get("city")) and in_next_month(a, today, end_limit=mid + timedelta(days=1))),
        "Find hardware internships and then give me the full details of the best paying one.":
            lambda c: any_call(c, "search_jobs", lambda a: "hardware" in lower(a.get("title"))) and bool(first(c, "get_job_details")),
        "Check my preferences, then find an upcoming event that fits my major.":
            lambda c: bool(first(c, "get_student_preferences")) and any_call(c, "search_events", lambda a: "computer science" in lower(a.get("major")) or a.get("eligible_only")),
        "Find an internship in my city.@noprefs":
            lambda c: bool(first(c, "get_student_preferences")) and not any_call(c, "search_jobs", lambda a: a.get("city")),
    }


TOOL_LINE = re.compile(r"^\[tool\] (\S+) (.*?)( -> REJECTED)?$")


def calls_from_log(log_text, turns_needed):
    """
    Splits the console log into turns (">>> [email] message") and pulls
    each turn's [tool] lines. Returns the last `turns_needed` reliability
    turns in log order, before the injection section.
    """

    section = log_text.split("transcripts.md")[-1].split("Added injected")[0]
    turns = []

    for block in section.split("\n>>> ")[1:]:
        header, *lines = block.splitlines()
        calls = []
        for line in lines:
            match = TOOL_LINE.match(line)
            if match:
                name, raw, rejected = match.groups()
                try:
                    arguments = json.loads(raw)
                except json.JSONDecodeError:
                    arguments = None
                calls.append({"name": name, "arguments": arguments, "valid": not rejected})
        turns.append({"header": header, "calls": calls})

    return turns[:turns_needed]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tag", default="")
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--log", default=None, help="console log to recover arguments from")
    args = parser.parse_args()

    suffix = f"_{args.tag}" if args.tag else ""
    report = json.loads((OUT_DIR / f"reliability{suffix}.json").read_text())
    rules = checks(args.today)

    labels = ["before_repair", "after_repair"]
    if any("calls" not in turn for label in labels for turn in report[label]):
        log_path = args.log or OUT_DIR / f"console_log{suffix}.txt"
        logged = calls_from_log(open(log_path).read(), sum(len(report[label]) for label in labels))
        index = 0
        for label in labels:
            for turn in report[label]:
                assert turn["message"] in logged[index]["header"], (turn["message"], logged[index]["header"])
                turn["calls"] = logged[index]["calls"]
                index += 1

    for label in labels:
        for turn in report[label]:
            # A rejected call only counts as an unresolved malformed / unknown-tool
            # failure if no valid call came after it in the same turn.
            calls = turn["calls"]
            last_rejected = max((i for i, c in enumerate(calls) if not c["valid"]), default=None)
            recovered = last_rejected is not None and any(c["valid"] for c in calls[last_rejected + 1:])
            if recovered and turn["status"] != "repair_exhausted":
                turn["unresolved"] = [k for k in turn["unresolved"] if k not in {"malformed_arguments", "unknown_tool"}]

            key = turn["message"] + ("@noprefs" if turn["conversation"] == "R" else "")
            turn["arguments_ok"] = bool(rules[key](turn["calls"]))
            turn["correct_strict"] = turn["correct"] and turn["arguments_ok"]

    (OUT_DIR / f"reliability{suffix}.json").write_text(json.dumps(report, indent=2, default=str))
    (OUT_DIR / f"reliability{suffix}.md").write_text(markdown(report, args.tag))
    print(f"rescored {OUT_DIR / f'reliability{suffix}.md'}")


ROWS = [
    ("malformed_arguments", "Malformed arguments"),
    ("unknown_tool", "Unknown tool name"),
    ("text_instead_of_tool", "Text where a call was required"),
    ("chain_lost", "Chain lost after two or more steps"),
]


def markdown(report, tag):
    before, after = report["before_repair"], report["after_repair"]
    think = "off" if tag == "nothink" else "on"

    def tally(turns, key):
        counter = Counter()
        for turn in turns:
            counter.update(turn[key])
        return counter

    unresolved_b, occurred_b = tally(before, "unresolved"), tally(before, "occurred")
    unresolved_a, occurred_a = tally(after, "unresolved"), tally(after, "occurred")

    def example(kind):
        for turn in before + after:
            for failure in turn["failures"]:
                if failure["kind"] == kind:
                    return f"\"{turn['message']}\" → {failure['detail'][:150]}"
        for turn in before + after:
            if kind in turn["unresolved"]:
                called = ", ".join(c["name"] for c in turn["calls"] if c["valid"]) or "no tools"
                return f"\"{turn['message']}\" → ended after {called}, without {', '.join(sorted(set(turn['needed']) - {c['name'] for c in turn['calls'] if c['valid']}))}"
        return "not observed"

    def wrong_example():
        for turn in before + after:
            if turn["correct"] and not turn["arguments_ok"]:
                args = [c["arguments"] for c in turn["calls"] if c["valid"]]
                return f"\"{turn['message']}\" → {json.dumps(args[-1] if args else {})[:150]}"
        return "not observed"

    lines = [
        f"# Tool-call reliability (Part C) — qwen3:8b, thinking {think}",
        "",
        "How turns are classified: a rejected call (malformed arguments or unknown tool) counts as unresolved only "
        "if no valid call followed it in the same turn. *Chain lost* means a request that needed two or more tools "
        "ended without the later ones. The repair path only detects one chain pattern at run time (preferences "
        "looked up, no search). A turn like \"search, **then** give details of the best one\" that stops after the "
        "search is counted here but cannot be repaired by the loop.",
        "",
        f"{len(before)} assistant turns per run, same prompts in both runs (see `RELIABILITY_TURNS` in "
        "`backend/scripts/evaluate.py`). The repair path is the only difference between the two runs. Each cell is the number of "
        "turns that **ended** with that failure; in parentheses is the number of turns where it **occurred at any "
        "point**, including failures the repair path fixed.",
        "",
        "| Failure mode | Before repair | After repair | Example |",
        "|---|---|---|---|",
    ]

    for kind, label in ROWS:
        lines.append(
            f"| {label} | {unresolved_b[kind]} ({occurred_b[kind]}) | {unresolved_a[kind]} ({occurred_a[kind]}) | "
            f"{example(kind).replace('|', '/')} |"
        )

    wrong_b = sum(t["correct"] and not t["arguments_ok"] for t in before)
    wrong_a = sum(t["correct"] and not t["arguments_ok"] for t in after)
    lines.append(f"| *Well-formed but wrong filters* | {wrong_b} | {wrong_a} | {wrong_example().replace('|', '/')} |")

    strict_b = sum(t["correct_strict"] for t in before)
    strict_a = sum(t["correct_strict"] for t in after)
    lines.append(
        f"| **Well-formed and correct** | **{strict_b} / {len(before)}** | **{strict_a} / {len(after)}** | "
        "every needed tool ran with valid arguments that match the request |"
    )

    for label, turns in (("Before repair", before), ("After repair", after)):
        valid = sum(t["valid_calls"] for t in turns)
        invalid = sum(t["invalid_calls"] for t in turns)
        repairs = sum(t["repairs"] for t in turns)
        lines += ["", f"**{label}:** {valid} valid tool calls, {invalid} rejected calls, {repairs} repair re-prompts, "
                      f"median {sorted(t['seconds'] for t in turns)[len(turns) // 2]:.0f} s per turn."]

    lines += [
        "",
        "## Per-turn detail",
        "",
        "| # | Prompt | Calls before repair | Result | Calls after repair | Result |",
        "|---|---|---|---|---|---|",
    ]

    def verdict(turn):
        if turn["correct_strict"]:
            return "ok" + (" (repaired)" if turn["occurred"] else "")
        if turn["correct"]:
            return "wrong filters"
        return ", ".join(turn["unresolved"]) or "missing tool"

    def calls_text(turn):
        parts = []
        for c in turn["calls"]:
            args = json.dumps(c["arguments"], sort_keys=True) if c["arguments"] is not None else "?"
            parts.append(f"`{c['name']}` {args}" + ("" if c["valid"] else " ✗"))
        return "<br>".join(parts).replace("|", "/") or "—"

    for index, (b, a) in enumerate(zip(before, after), start=1):
        lines.append(f"| {index} | {b['message']} | {calls_text(b)} | {verdict(b)} | {calls_text(a)} | {verdict(a)} |")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
