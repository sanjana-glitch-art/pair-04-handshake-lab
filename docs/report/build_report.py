"""
Builds LabPair-04_Lab1_Report.pdf from the report template and the
evaluation outputs in docs/evaluation/, so the numbers in the PDF are
exactly the measured ones.

    backend/.venv/bin/python docs/report/build_report.py

Needs pandoc and xelatex.
"""

import re
import subprocess
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent
EVAL_DIR = REPORT_DIR.parent / "evaluation"
TEMPLATE = REPORT_DIR / "LabPair-04_Lab1_Report.md"
FILLED = REPORT_DIR / "build" / "report_filled.md"
PDF = REPORT_DIR / "LabPair-04_Lab1_Report.pdf"


def read(name):
    path = EVAL_DIR / name
    return path.read_text() if path.exists() else f"*{name} has not been generated yet.*"


def section(markdown_text, start, end=None):
    """
    Returns the text from the first line starting with `start` up to the
    first line starting with `end` (exclusive).
    """

    lines = markdown_text.splitlines()
    begin = next((i for i, line in enumerate(lines) if line.startswith(start)), None)
    if begin is None:
        return ""
    stop = len(lines)
    if end:
        stop = next((i for i, line in enumerate(lines[begin + 1:], begin + 1) if line.startswith(end)), len(lines))
    return "\n".join(lines[begin:stop]).strip()


def demote(markdown_text, levels=2):
    return re.sub(r"^(#+) ", lambda m: "#" * (len(m.group(1)) + levels) + " ", markdown_text, flags=re.M)


def shorten_code_blocks(markdown_text, max_lines=14):
    """
    Long tool results make the PDF hard to read; keep the head of each
    block and point to the full transcript file.
    """

    def trim(match):
        body = match.group(2).splitlines()
        if len(body) <= max_lines:
            return match.group(0)
        kept = "\n".join(body[:max_lines])
        return f"{match.group(1)}{kept}\n… ({len(body) - max_lines} more lines in docs/evaluation/transcripts.md)\n```"

    return re.sub(r"(```text\n)(.*?)\n```", trim, markdown_text, flags=re.S)


def strip_console_blocks(markdown_text):
    return re.sub(r"Console output:\n\n```text\n.*?\n```\n", "", markdown_text, flags=re.S)


REPO = REPORT_DIR.parents[1]


def function_source(relative_path, name):
    """
    Source of one top-level function, found with ast so line numbers
    never go stale.
    """

    import ast

    source = (REPO / relative_path).read_text()
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node)
    raise ValueError(f"{name} not found in {relative_path}")


def between(relative_path, start, end):
    text = (REPO / relative_path).read_text()
    begin = text.index(start)
    return text[begin:text.index(end, begin)].rstrip()


def code_block(title, path, body, language="python"):
    return f"**{title}** — `{path}`\n\n```{language}\n{body}\n```\n"


def code_section():
    parts = [
        code_block("Model client interface", "backend/app/assistant/model_client.py",
                   between("backend/app/assistant/model_client.py", "class ModelClient(ABC):", "# Some models")),
        code_block("Agent loop with iteration ceiling, logging, and repair", "backend/app/assistant/agent.py",
                   function_source("backend/app/assistant/agent.py", "run_assistant")),
        code_block("Running one tool call: validation, repair message, confirmation gate", "backend/app/assistant/agent.py",
                   function_source("backend/app/assistant/agent.py", "_run_one_call")),
        code_block("Confirmation gate", "backend/app/assistant/confirm.py",
                   function_source("backend/app/assistant/confirm.py", "confirm_action")),
        code_block("Untrusted-data defense", "backend/app/assistant/tools.py",
                   function_source("backend/app/assistant/tools.py", "neutralize") + "\n\n\n"
                   + function_source("backend/app/assistant/tools.py", "wrap_untrusted")),
        code_block("One tool schema (get_job_details)", "backend/app/assistant/tools.py",
                   between("backend/app/assistant/tools.py", '    {\n        "type": "function",\n        "function": {\n            "name": "get_job_details"',
                           '    {\n        "type": "function",\n        "function": {\n            "name": "search_events"')),
        code_block("Tool executor: always returns a string", "backend/app/assistant/tools.py",
                   function_source("backend/app/assistant/tools.py", "execute_tool")),
        code_block("Seed generator: every random value comes from Random(SEED)", "database/seed/generate_seed.py",
                   between("database/seed/generate_seed.py", "def build_rows(anchor):", "    skill_ids =")),
    ]
    return "\n".join(parts)


def terminal_section():
    nothink_log = read("console_log_nothink.txt")
    blocks = nothink_log.split("\n>>> ")[1:]
    after_repair = blocks[len(blocks) // 2:]  # the second run has the repair path on

    def fixed_malformed(block):
        lines = block.splitlines()
        rejected = [i for i, line in enumerate(lines) if line.endswith("-> REJECTED")]
        return rejected and any(
            line.startswith("[tool]") and not line.endswith("REJECTED") for line in lines[rejected[0]:]
        )

    examples = [b for b in after_repair if fixed_malformed(b)][:1] + [b for b in after_repair if "[repair]" in b][:1]
    repair_example = "\n\n".join(">>> " + b.strip() for b in examples) or "(no repair observed)"

    pytest_tail = "\n".join(read("pytest_output.txt").splitlines()[-6:])
    run_log = (REPO / "RUN_LOG.txt").read_text()
    seed = run_log[run_log.index("$ backend/.venv/bin/python database/seed/generate_seed.py --reset"):run_log.index("# Determinism")].strip()

    return (
        "**Seeding the database**\n\n```text\n" + seed + "\n```\n\n"
        "**Test suite** (`cd backend && .venv/bin/python -m pytest -v`)\n\n```text\n" + pytest_tail + "\n```\n\n"
        "**The repair path in action** (reasoning-off run, repair on). First: the model invents an argument, the call "
        "is rejected with the specific error, and the corrected call runs. Second: the model answers from memory, "
        "is re-prompted once, and makes the real lookup.\n\n```text\n" + repair_example[:2500] + "\n```\n\n"
        "Full console logs: `docs/evaluation/console_log*.txt`. Every command we ran is in `RUN_LOG.txt`."
    )


def wrap_code_lines(markdown_text, width=88):
    """
    LaTeX does not wrap code blocks, so long lines are broken here with a
    continuation marker, keeping the original indentation.
    """

    out, in_code = [], False

    for line in markdown_text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            out.append(line)
            continue

        if not in_code or len(line) <= width:
            out.append(line)
            continue

        indent = " " * (len(line) - len(line.lstrip()) + 4)
        out.append(line[:width] + " ↩")
        rest = line[width:]
        while rest:
            chunk_width = width - len(indent)
            out.append(indent + rest[:chunk_width] + (" ↩" if len(rest) > chunk_width else ""))
            rest = rest[chunk_width:]

    return "\n".join(out)


def build():
    template = TEMPLATE.read_text()
    transcripts = read("transcripts.md")
    reliability = read("reliability.md")
    reliability_nothink = read("reliability_nothink.md")
    injection = read("injection.md")
    pytest_output = read("pytest_output.txt")

    tests_body = transcripts.split("\n### ", 1)
    summary = section(transcripts, "| Test", "### ")
    five = "### " + tests_body[1].split("## Confirmation gate")[0] if len(tests_body) > 1 else transcripts

    replacements = {
        "<!-- API_TESTS -->": (
            "`backend/tests/` holds 38 pytest tests run with FastAPI's TestClient against the seeded "
            "database. They cover authentication, role and ownership checks (403/404), input validation (422), "
            "search filters, eligibility, resume access control, and the agent loop with a scripted fake "
            "model (iteration ceiling, repair path, confirmation decline, unknown tools, untrusted-data fence). "
            "The Postman collection in `docs/api/` has a saved live response for each endpoint.\n\n"
            "```text\n" + "\n".join(line for line in pytest_output.splitlines() if "PASSED" in line or "FAILED" in line or "passed" in line) + "\n```"
        ),
        "<!-- TRANSCRIPTS -->": (
            "All five tests ran with `qwen3:8b`, the defense on, and the repair path on. "
            "T4 was sent in the same conversation as T1. Full tool results are in "
            "`docs/evaluation/transcripts.md`; here long results are trimmed.\n\n"
            + summary + "\n\n" + shorten_code_blocks(strip_console_blocks(demote(five, 0)))
        ),
        "<!-- CONFIRMATION -->": (
            "`confirm_action(tool_name, arguments, auto_approve=False)` is in "
            "`backend/app/assistant/confirm.py`. The loop calls it before any tool in `GATED_TOOLS` "
            "(only `save_job_or_event`); read-only tools never ask. A decline returns a `CANCELLED: …` "
            "string to the model as the tool result. In the web app the request pauses and the UI shows Yes / No.\n\n"
            + shorten_code_blocks(strip_console_blocks(demote(section(transcripts, "## Confirmation gate").split("\n", 1)[-1], 1)))
        ),
        "<!-- INJECTION -->": (
            "Queries: T1 internship in my city; T2 remote data science internship (Python, SQL); "
            "T3 event for CS students next month; T4 follow-up \"closer or higher paying\"; "
            "T5 marine biology job at SpaceX.\n\n"
            + demote(re.sub(r"^\| (T\d) [^|]*\|", r"| \1 |", injection.split("\n", 1)[-1].split("## Answers")[0], flags=re.M), 1)
            + "\n\nA first run was invalid and is kept for the record "
            "(`docs/evaluation/injection_run1_truncated.md`): its injected text was longer than the "
            "160-character summary that search results show, so the instructions never reached the model. "
            "The fixture was shortened to 147 characters and placed first, and the table above is the repeated "
            "run. Full answers are in `docs/evaluation/injection.md`."
        ),
        "<!-- RELIABILITY -->": (
            "Repair path (`backend/app/assistant/agent.py`): a rejected call (unknown tool, unexpected or missing "
            "argument, wrong type or enum, unparseable JSON) or a text answer that skipped required tool work gets "
            "**one** re-prompt that names the specific error. A run allows at most **two** re-prompts; after that "
            "it stops with a clear message instead of guessing.\n\n"
            "We ran the same 24 turns with qwen3 reasoning on (the shipped configuration) and off, each with the "
            "repair path off and then on.\n\n"
            + demote(section(reliability, "# Tool-call reliability", "## Per-turn detail"), 2)
            + "\n\n"
            + demote(section(reliability_nothink, "# Tool-call reliability", "## Per-turn detail"), 2)
        ),
        "<!-- EVIDENCE -->": (
            "Console output from `backend/scripts/evaluate.py`, showing the one-line-per-tool-call log and "
            "the tool-call count after each run (the first three required tests):\n\n```text\n"
            + "\n".join(read("console_log_transcripts.txt").splitlines()[:13])
            + "\n```"
        ),
        "<!-- CODE -->": code_section(),
        "<!-- TERMINAL -->": terminal_section(),
    }

    filled = template
    for marker, content in replacements.items():
        filled = filled.replace(marker, content)

    assistant_shot = REPORT_DIR / "screenshots" / "student_assistant.jpg"
    filled = filled.replace(
        "<!-- ASSISTANT_SCREENSHOT -->",
        "![AI assistant: answer with its tool call, then the Yes / No confirmation for a save](screenshots/student_assistant.jpg){width=90%}\n\n"
        "![The student declines; nothing is saved and the assistant does not retry](screenshots/student_assistant_declined.jpg){width=90%}"
        if assistant_shot.exists() else "",
    )

    filled = wrap_code_lines(filled)

    # The PDF fonts lack these glyphs.
    filled = filled.replace("→", "->").replace("✗", "(rejected)").replace(" ↩", " \\")

    FILLED.parent.mkdir(exist_ok=True)
    FILLED.write_text(filled)

    subprocess.run(
        [
            "pandoc", str(FILLED), "-o", str(PDF),
            "--pdf-engine=xelatex",
            f"--resource-path={REPORT_DIR}",
            "-V", "mainfont=Helvetica",
            "-V", "monofont=Menlo",
            "-V", "tables=true",
            "--toc",
        ],
        check=True,
    )
    print(f"wrote {PDF}")


if __name__ == "__main__":
    build()
