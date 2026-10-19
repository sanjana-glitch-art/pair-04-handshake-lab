# Pair 04 — Handshake prototype with a hand-built AI assistant (Lab 1)

A Handshake-style career platform for students and companies, built with
React, FastAPI, and MySQL, plus an AI career assistant whose agent loop is
written by hand (no LangChain, LlamaIndex, CrewAI, or other framework) and
runs on a local Ollama model.

Partners: Thummalapalli Sai Teja Sri Sanjana and Karthik Pragada.

Repository: https://github.com/sanjana-glitch-art/pair-04-handshake-lab (Lab 1 submission: tag `lab1`)

## Pair parameters

| Parameter | Value | Where it is used |
|---|---|---|
| PAIR | 04 | `.env` (`PAIR=4`) |
| PORT_BASE | 9000 + 4 × 10 = **9040** | backend port; frontend `VITE_API_BASE_URL` default |
| Database and Kafka prefix | **p4** | database `p4_handshake` |
| SEED | **4** | `random.Random(4)` in the seed generator; Ollama `seed` option |
| CITY_SET | **San Jose, Santa Clara, Milpitas** | seed generator, preference and job city filters |

## Architecture

```
React (Vite, Bootstrap)  ──Fetch/JSON──▶  FastAPI (port 9040)  ──SQLAlchemy──▶  MySQL p4_handshake
     frontend/src                              backend/app                           database/schema.sql
                                                   │
                                                   └── app/assistant/  ──HTTP──▶  Ollama (qwen3:8b)
                                                        agent.py        hand-built loop, repair path
                                                        tools.py        5 tools + JSON schemas
                                                        confirm.py      confirm_action gate
                                                        model_client.py ModelClient.complete(messages, tools)
```

- **Auth:** bcrypt password hashes, JWT bearer tokens (`/auth/login`), role
  checks (`require_student`, `require_company`) on every protected route.
  Sign-out discards the token on the client.
- **Uploads:** resumes (PDF, 5 MB) and profile pictures (PNG/JPEG, 2 MB) are
  checked by file signature. Pictures are public under `/uploads/pictures`;
  resumes are only reachable through
  `GET /employer/applications/{id}/resume`, which checks that the company
  owns the job.
- **Assistant:** `ModelClient.complete(messages, tools)` is the only code
  that talks to Ollama. `run_assistant(user_message, conversation)` sends
  the system prompt, history, and tool schemas; runs requested tools;
  appends assistant and tool messages; and repeats until a final answer
  or `MAX_ITERATIONS = 6`. Each tool call prints one line and each run
  prints its tool-call count.

## Setup

Prerequisites: Python 3.11+, Node 20+, Docker (or a local MySQL 8), and
[Ollama](https://ollama.com) with the default model pulled:

```bash
ollama pull qwen3:8b
```

1. **Configuration.** Copy `.env.example` to `.env` and set the MySQL
   password (and port if not 3306). `.env` is git-ignored.

2. **MySQL.** Any MySQL 8 works. With Docker:

   ```bash
   docker run -d --name p4-mysql -e MYSQL_ROOT_PASSWORD=<password> -p 3307:3306 mysql:8.0
   ```

3. **Backend.**

   ```bash
   cd backend
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   cd ..
   ```

4. **Schema and seed data.** Creates `p4_handshake` from
   `database/schema.sql` and loads the generated data:

   ```bash
   backend/.venv/bin/python database/seed/generate_seed.py --reset
   ```

5. **Run the API** (Swagger UI at http://127.0.0.1:9040/docs):

   ```bash
   cd backend && .venv/bin/uvicorn app.main:app --port 9040
   ```

6. **Run the frontend** (http://localhost:5173):

   ```bash
   cd frontend && npm install && npm run dev
   ```

### Demo accounts

Every seeded account uses the password `Pair4Demo!`.

| Account | Email | Notes |
|---|---|---|
| Student | `demo.student@example.edu` | San Jose, Computer Science, saved preferences |
| Student | `noprefs.student@example.edu` | no saved preferences (tests that path) |
| Company | `demo.company@example.com` | TechNova Solutions |

## Seed data

`database/seed/generate_seed.py` uses `random.Random(SEED)` for every
choice, so the same SEED always produces the same rows (verified by
comparing `CHECKSUM TABLE` across two runs). Dates are offsets from the run
date so events stay upcoming; pass `--anchor-date YYYY-MM-DD` to pin them.

| Table | Rows | Required |
|---|---|---|
| companies | 50 | 50 |
| students | 200 | 200 |
| jobs | 320 | 300 |
| applications | 1,500 | 1,500 |
| events | 110 | 100 |
| skills / student skills / job skills | 30 / 834 / 842 | — |
| event registrations | 600 | — |
| student preferences | 140 | — |

## API documentation

- Swagger UI: http://127.0.0.1:9040/docs (live, from FastAPI). Click
  **Authorize** and sign in with a demo account (username = email).
- `docs/api/openapi.json` and `docs/api/openapi.yaml`: exported OpenAPI schema
- `docs/api/swagger.html`: standalone Swagger UI with the schema embedded;
  open it in a browser without running the backend
- `docs/api/pair4_handshake.postman_collection.json`: Postman collection
  with parameters, headers, and saved sample responses

Regenerate both with the API running:

```bash
backend/.venv/bin/python backend/scripts/export_api_docs.py
```

## AI assistant

Use it in the web app (student sidebar → AI Assistant), where each answer
lists its tool calls and a save asks Yes / No, or in the terminal:

```bash
backend/.venv/bin/python backend/scripts/assistant_cli.py
backend/.venv/bin/python backend/scripts/assistant_cli.py --no-defense --no-repair
```

| Requirement | Where |
|---|---|
| Model client interface + Ollama implementation | `backend/app/assistant/model_client.py` |
| `run_assistant`, iteration ceiling, per-call log line, call count | `backend/app/assistant/agent.py` |
| Five tools, JSON schemas, always return strings | `backend/app/assistant/tools.py` |
| `confirm_action(tool_name, arguments, auto_approve=False)` | `backend/app/assistant/confirm.py` |
| Untrusted-data labelling and delimiters (injection defense) | `wrap_untrusted` in `tools.py`, rule 7 in `agent.py` |
| Repair path (one targeted re-prompt per failure, max 2, clean stop) | `_run_one_call` / `_check_text_answer` in `agent.py` |
| HTTP endpoints `/assistant/chat`, `/assistant/confirm` | `backend/app/assistant_routes.py` |

### Evaluations

```bash
backend/.venv/bin/python database/seed/generate_seed.py --reset
backend/.venv/bin/python backend/scripts/evaluate.py all
backend/.venv/bin/python backend/scripts/score_reliability.py
backend/.venv/bin/python backend/scripts/evaluate.py reliability --no-think --tag nothink
backend/.venv/bin/python backend/scripts/score_reliability.py --tag nothink
backend/.venv/bin/python backend/scripts/write_metrics.py
backend/.venv/bin/python docs/report/build_report.py
```

These write `docs/evaluation/transcripts.md` (the five required tests plus
the confirmation gate), `reliability.md` and `reliability_nothink.md` (24
turns, repair off vs on), and `injection.md` (five queries with injected
postings, defense off vs on). `METRICS.md` and the report PDF are built
from those files. With reasoning on, a full run takes about 2 hours on an
M4 Mac.

### Tests

```bash
cd backend && .venv/bin/python -m pytest -v
```

The suite has 38 tests: API tests through FastAPI's TestClient, and
agent-loop tests that use a scripted fake model. They need the seeded
database but not Ollama.

## Repository layout

```
backend/app/            FastAPI app: routes, models, schemas, security
backend/app/assistant/  hand-built agent loop, tools, confirmation gate, model client
backend/scripts/        assistant CLI, evaluations, scoring, metrics, API doc export
backend/tests/          pytest suite (API + agent loop with a scripted model)
database/schema.sql     MySQL schema
database/seed/          seed generator and prompt-injection fixture
docs/api/               OpenAPI + Postman collection
docs/evaluation/        transcripts, reliability, injection results, console logs
docs/report/            report source, screenshots, build script, PDF
frontend/src/           React pages, components, layouts, services
METRICS.md  RUN_LOG.txt  AI_USE.md
```
