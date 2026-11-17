"""
Guardrail helpers that are not part of tool validation itself.

The eight guardrails and where each one is enforced:

1. Tool allowlist ......... validate_arguments (tools.py): unknown names are rejected
2. Schema validation ...... validate_arguments (tools.py): types, enums, extra/missing args
3. Authorization .......... require_student on every assistant route; tools only ever
                            use ctx.student_id from the signed-in session; the save
                            tool calls the Student service with the student's own token
4. Read/write control ..... READ_ONLY_TOOLS run directly; GATED_TOOLS go through
                            confirm_action (confirm.py)
5. Injection defense ...... wrap_untrusted / neutralize (tools.py) + rule 7 (agent.py)
6. Privacy and secrets .... redact() below, applied to every answer and to logged
                            tool arguments; rule 8 in the system prompt
7. Bounded execution ...... MAX_ITERATIONS, per-call HTTP timeout, a whole-request
                            deadline, and at most one repair re-prompt per failure (agent.py)
8. Reliable answers ....... tools return explicit no-match / error text; rule 1;
                            _check_text_answer forces a tool call for data questions
"""

import re


REDACTED = "[redacted]"

SECRET_PATTERNS = [
    # JWTs (three base64url segments).
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "[redacted token]"),
    # Bearer tokens.
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"), "Bearer [redacted token]"),
    # AWS access key ids and common API key shapes.
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[redacted key]"),
    ("api_key", re.compile(r"\b(sk|pk|rk)[-_](live|test|proj)?[-_]?[A-Za-z0-9]{16,}\b"), "[redacted key]"),
    # password=..., "password": "...", api_key: ..., secret=...
    ("password_or_secret", re.compile(r"(?i)\b(password|passwd|pwd|api[_-]?key|secret|token|access[_-]?key)(\s*[:=]\s*|\"\s*:\s*\")([^\s\",;]{3,})"),
     lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}"),
    # bcrypt hashes.
    ("bcrypt_hash", re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}"), "[redacted hash]"),
]

# Student accounts use .edu addresses. Company contact emails in job
# postings are public, so only .edu addresses that are not the signed-in
# student's own are treated as another student's private data.
STUDENT_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.edu\b", re.I)


def redact(text: str | None, own_email: str | None = None) -> tuple[str, list[str]]:
    """
    Returns (clean_text, list_of_what_was_redacted).
    """

    if not text:
        return text or "", []

    found: list[str] = []

    for name, pattern, replacement in SECRET_PATTERNS:
        if pattern.search(text):
            found.append(name)
            text = pattern.sub(replacement, text)

    def hide_email(match: re.Match) -> str:
        if own_email and match.group(0).lower() == own_email.lower():
            return match.group(0)
        found.append("student_email")
        return "[redacted email]"

    text = STUDENT_EMAIL.sub(hide_email, text)
    return text, found


def redact_value(value):
    """
    Redacts strings inside tool arguments before they are logged.
    """

    if isinstance(value, str):
        return redact(value)[0]
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value
