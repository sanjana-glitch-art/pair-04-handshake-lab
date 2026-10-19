---
title: "Lab 1 — Handshake Prototype with a Hand-Built AI Assistant"
subtitle: "Distributed Systems for Data Engineering · Lab Pair 04"
author: "Thummalapalli Sai Teja Sri Sanjana · Karthik Pragada"
date: "October 2026"
geometry: margin=0.9in
fontsize: 10pt
colorlinks: true
header-includes:
  - \usepackage{float}
  - \floatplacement{figure}{H}
---

# 1. Goals

1. Build a responsive Handshake-style web application with two personas,
   Student and Company, using React, FastAPI, and MySQL (Part A).
2. Implement an AI career assistant as a hand-written agent loop over five
   tools that read and write our own application data, running on a local
   Ollama model with no agent framework (Part B).
3. Add a human confirmation gate for state-changing tools, defend against
   prompt injection in user-generated content, and measure and repair
   tool-call failures (Part C).

# 2. Pair parameters

| Parameter | Derivation | Value |
|---|---|---|
| PAIR | assigned on Canvas | 04 |
| PORT_BASE | 9000 + PAIR × 10 | 9040 |
| Database and Kafka prefix | p{PAIR} | p4 (database `p4_handshake`) |
| SEED | PAIR | 4 |
| CITY_SET | assigned on Canvas | San Jose, Santa Clara, Milpitas |

# 3. System design

```
React + Bootstrap  --JSON-->  FastAPI :9040  --SQLAlchemy-->  MySQL p4_handshake
                                   |
                                   +--> app/assistant/  --HTTP-->  Ollama qwen3:8b
                                          agent.py         run_assistant + repair path
                                          tools.py         5 tools, schemas, data fence
                                          confirm.py       confirm_action gate
                                          model_client.py  complete(messages, tools)
```

**Backend.** FastAPI routers per area: `auth`, `students`, `jobs`,
`applications`, `events`, `preferences`, `saved`, `assistant`, and
`employer` (jobs, applications, events, profile). Pydantic models validate
every request body and query parameter: lengths, e-mail format, enums for
category and status, CGPA range, and phone format. Passwords are hashed
with bcrypt. Login returns a JWT that carries the user id and role;
`require_student` and `require_company` dependencies enforce roles, and
ownership checks return 404 for another company's applications or events.
Uploads are checked by file signature, not file name. Resumes are PDFs up
to 5 MB and are only served through an authorized preview endpoint.
Profile pictures are PNG or JPEG up to 2 MB and are served publicly.

**Database.** `database/schema.sql` defines `users`, `student_profiles`,
`company_profiles`, `skills` with the `student_skills` and `job_skills`
link tables, `jobs`, `applications` (unique per student and job),
`events`, `event_registrations` (unique per student and event),
`student_preferences`, and `saved_items`. Foreign keys cascade on delete,
and the columns used in searches are indexed.

**Frontend.** React with React Router and Bootstrap. Pages live in
`src/pages`, shared pieces in `src/components` (protected routes, error
and loading states), and every API call in `src/services/api.js`. Each
data-loading page shows loading and error states.

**Event eligibility.** One rule in `app/eligibility.py` is shared by
registration, the event list (`is_eligible`), the assistant's
`search_events`, and the seed generator. "All majors" or an empty field
is open to everyone. A major named in the text admits that major,
"Engineering students" admits any engineering major, and "Graduating
seniors (class of 2027)" admits students graduating that year.

## 3.1 AI assistant

- **Model client.** `ModelClient` is an abstract class with
  `complete(messages, tools)`. `OllamaModelClient` is the only code that
  calls Ollama (`/api/chat` with native tool calling). It normalizes
  replies into text plus `ToolCall` objects. Unparseable arguments, and
  tool calls the model wrote as text, become `ToolCall`s with a
  `parse_error` instead of exceptions. Options: `seed=4`, `temperature=0.2`,
  `num_ctx=12288` (Ollama's default 4,096-token window silently dropped
  older turns), and qwen3 reasoning on (see §6.3).
- **Loop.** `run_assistant(user_message, conversation)` appends the user
  message, then repeats: send system prompt, history, and the five tool
  schemas; if the model requests tools, validate and run each one and
  append the assistant message and one `tool` message per result;
  otherwise return the text answer. The hard ceiling is `MAX_ITERATIONS = 6`,
  after which the loop stops with a clear message. It prints one
  `[tool] name {args}` line per call and `[assistant] tool calls this run: N`
  after each run.
- **Tools.** Each tool has a plain-English description saying when to use
  it, typed parameters, and parameter descriptions. `validate_arguments`
  checks arguments against the schema (unknown keys, missing required
  values, types, enums). `execute_tool` catches every exception, so every
  tool returns a string in every case.
- **Web integration.** `/assistant/chat` keeps each student's conversation
  on the server, so follow-ups include earlier tool results. When the loop
  reaches a gated tool, the request pauses and the UI shows Yes / No;
  `/assistant/confirm` resumes the same turn with the decision.

# 4. Part A — platform

## 4.1 Feature checklist

| Requirement | Implementation |
|---|---|
| Student signup (name, email, password, college), bcrypt | `POST /auth/signup` |
| Sign in / sign out (JWT) | `POST /auth/login`; client discards the token |
| Profile with picture, skills, education, experience, contact | `GET/PUT /students/me`, `POST /students/me/picture` |
| Search jobs by title/company; filter category and city | `GET /jobs?search=&category=&city=` (open jobs by default) |
| Job details with company profile and contact | `GET /jobs/{id}` |
| Apply with PDF resume; list with date and status; status filter | `POST /applications`, `GET /applications/me?status=` |
| Upcoming events ascending; search; details; register when eligible; registered list | `GET /events`, `GET /events/{id}`, `POST /events/{id}/register`, `GET /events/registered` |
| Browse students by name/college, filter by major | `GET /students?name=&college=&major=` |
| AI assistant from the dashboard | sidebar + dashboard card → `/student/assistant` |
| Company signup, sign in/out | `POST /auth/company/signup` |
| Post / edit / delete jobs; view own postings and applicants | `/employer/jobs`, `GET /employer/applications?job_id=` |
| Student profile, resume preview, status update | `/students/{id}`, `/employer/applications/{id}/resume`, `PATCH .../status` |
| Company profile with picture | `GET/PUT /employer/profile`, `POST /employer/profile/picture` |
| Students tab: search by name, college, skillset | `GET /students?skill=` |
| Events tab: post events; view registered students and profiles | `/employer/events`, `GET /employer/events/{id}/registrations` |
| Swagger / Postman | `/docs`; `docs/api/` (OpenAPI JSON/YAML, standalone Swagger HTML, Postman collection), see §4.5 |

## 4.2 Seed data

`database/seed/generate_seed.py` draws every random value from
`random.Random(SEED=4)`. Running it twice produced identical
`CHECKSUM TABLE` values for jobs, applications, events, student profiles,
registrations, and job skills.

| Table | Rows | Required |
|---|---|---|
| Companies | 50 | 50 |
| Students | 200 | 200 |
| Job postings | 320 | 300 |
| Applications | 1,500 | 1,500 |
| Events | 110 | 100 |
| Skills / student skills / job skills | 30 / 834 / 842 | — |
| Event registrations (eligible only) | 600 | — |
| Student preferences | 140 | — |

All companies, jobs, events, and students are located in San Jose, Santa
Clara, or Milpitas (plus remote jobs).

## 4.3 Screenshots

![Login](screenshots/login.jpg){width=70%}

![Student job search with details panel](screenshots/student_jobs.jpg){width=90%}

![Student applications filtered to Declined](screenshots/student_applications.jpg){width=90%}

![Upcoming events with eligibility-aware Register buttons](screenshots/student_events.jpg){width=90%}

![Student profile with picture upload](screenshots/student_profile.jpg){width=90%}

![Company: resume preview for an applicant](screenshots/employer_resume_preview.jpg){width=90%}

![Company: Students tab searched by skill](screenshots/employer_students_skill_search.jpg){width=90%}

![Company: registered students for an event](screenshots/employer_event_registrants.jpg){width=90%}

<!-- ASSISTANT_SCREENSHOT -->

## 4.4 API tests

<!-- API_TESTS -->

## 4.5 API documentation

FastAPI serves interactive Swagger UI at `http://127.0.0.1:9040/docs`. It is
generated from the same Pydantic models that validate requests, so the
documented parameters, types, enums, and response schemas match the code.
The schema is exported to the repository in three forms:

| Export | Contents |
|---|---|
| OpenAPI schema: `openapi.json`, `openapi.yaml` | OpenAPI 3.1, 35 paths, 38 schemas |
| Standalone Swagger UI: `swagger.html` | Schema embedded; opens in a browser without the backend |
| Postman collection: `pair4_handshake.postman_collection.json` | 18 requests with parameters, auth headers, and saved live sample responses |

All files are in `docs/api/`.

![Swagger UI: authentication, student, job, application, and event endpoints](screenshots/swagger_1_overview.jpg){width=62%}

![Swagger UI: preferences, AI assistant, and employer endpoints](screenshots/swagger_2_assistant_employer.jpg){width=62%}

![Swagger UI: employer events, applications, profile, and saved items](screenshots/swagger_3_employer_saved.jpg){width=62%}

![Authorize dialog: Swagger signs in through the form-based /auth/token endpoint](screenshots/swagger_4_authorize.jpg){width=62%}

![Try it out on GET /jobs: query parameters and the generated curl command](screenshots/swagger_5_try_jobs_parameters.jpg){width=62%}

![The same request: request URL, HTTP 200, response body, and response headers](screenshots/swagger_6_try_jobs_response.jpg){width=62%}

# 5. Part B — assistant transcripts

<!-- TRANSCRIPTS -->

# 6. Part C — safety, injection, reliability

## 6.1 Confirmation gate

<!-- CONFIRMATION -->

## 6.2 Prompt injection before and after the defense

<!-- INJECTION -->

## 6.3 Tool-call reliability

<!-- RELIABILITY -->

# 7. Code walkthrough

The snippets below are extracted from the repository when this report is
built, so they match the submitted code.

<!-- CODE -->

# 8. Terminal output

<!-- TERMINAL -->

# 9. Assistant tool-call evidence

<!-- EVIDENCE -->

# Appendix A: Swagger UI endpoint details

Expanded Swagger UI views (`http://127.0.0.1:9040/docs`) of the main
endpoints for each persona and the AI assistant: parameters, request body
example, and success response. Every endpoint can also return `422` with
field-level validation errors, so that response is hidden here. The full
schema is in `docs/api/openapi.json` and `docs/api/swagger.html`.

![POST /auth/login: JSON credentials in, JWT out (used by the React app)](screenshots/api/01_auth_login.png){width=88%}

![PUT /students/me: profile update with every editable field, including skills](screenshots/api/02_students_me_put.png){width=88%}

![GET /students: student directory with name, college, major, and skill filters](screenshots/api/03_students_search.png){width=88%}

![POST /applications: multipart upload of job_id and the PDF resume](screenshots/api/04_applications_post.png){width=88%}

![POST /events/{event_id}/register: registration, refused when the student is not eligible](screenshots/api/05_events_register.png){width=88%}

![POST /assistant/chat: one student message through the agent loop; returns tool calls and any pending confirmation](screenshots/api/06_assistant_chat.png){width=88%}

![POST /assistant/confirm: the student approves or declines the paused save](screenshots/api/07_assistant_confirm.png){width=88%}

![POST /employer/jobs: a company creates a job posting](screenshots/api/08_employer_jobs_post.png){width=88%}

![PATCH /employer/applications/{application_id}/status: Pending, Reviewed, or Declined](screenshots/api/09_employer_application_status.png){width=88%}

![GET /employer/applications/{application_id}/resume: inline PDF preview, owning company only](screenshots/api/10_employer_application_resume.png){width=88%}

![GET /employer/events/{event_id}/registrations: students registered for a company's event](screenshots/api/11_employer_event_registrations.png){width=88%}

# Appendix B: Git commit history

Commit history of `main` in
`github.com/sanjana-glitch-art/pair-04-handshake-lab`, showing commits by
both partners (Thummalapalli Sai Teja Sri Sanjana as `sanjana-glitch-art`,
Karthik Pragada as `prags8585`).

![Git commit history of main](screenshots/git_commit_history.jpg){height=85%}
