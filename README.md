# Pair 04 — Handshake prototype with a hand-built AI assistant

A Handshake-style career platform for students and companies with an AI
career assistant whose agent loop is written by hand (no LangChain,
LlamaIndex, CrewAI, or other framework) and runs on a local Ollama model.

- **Lab 1** (tag `lab1`): React + FastAPI + MySQL, the assistant, its
  evaluations.
- **Lab 2** (tag `lab2`): the same platform split into six containerized
  services, orchestrated with Kubernetes, with Kafka for asynchronous
  flows, MongoDB instead of MySQL, Redux in the frontend, JMeter load
  tests, and an assistant with persistent memory, context compaction,
  tracing, and a guardrail harness.

Partners: Thummalapalli Sai Teja Sri Sanjana and Karthik Pragada.

Repository: https://github.com/sanjana-glitch-art/pair-04-handshake-lab

## Pair parameters

| Parameter | Value | Where it is used |
|---|---|---|
| PAIR | 04 | `.env` (`PAIR=4`) |
| PORT_BASE | 9000 + 4 × 10 = **9040** | gateway port 9040; services 9041-9046; Kafka host port 9047 |
| Database and Kafka prefix | **p4** | MongoDB database `p4_handshake`; Kafka topics `p4.*`; images, containers, namespace `p4-handshake` |
| SEED | **4** | `random.Random(4)` in the seed generator; Ollama `seed` option |
| CITY_SET | **San Jose, Santa Clara, Milpitas** | seed generator, preference and job city filters |

Seed counts (MongoDB): 50 companies, 200 students, 320 jobs, 1,500
applications, 110 events, 600 registrations, 140 preference sets, 30
skills, 64 memory entries for the demo student.

## Architecture (Lab 2)

```
Browser ── http://<host>:9040 ──▶ p4-frontend (nginx: React build + API gateway /api/*)
                                     │  Kubernetes service discovery / Compose DNS
     ┌───────────────┬───────────────┼────────────────┬──────────────────┬──────────────────┐
     ▼               ▼               ▼                ▼                  ▼                  ▼
 p4-student-     p4-company-     p4-job-          p4-application-    p4-event-          p4-assistant-
 service :9041   service :9042   service :9043    service :9044      service :9045      service :9046
 auth, sessions, company signup  search, postings apply, withdraw,   events, register   agent loop, memory,
 profiles, prefs, & profile      ─job.created─▶   status (company)   ─registration─▶    compaction, tokens
 saved, pictures                                  ─application.*─▶                      ─interaction/consolidate─▶
     │               │               │                │                  │                  │  │ HTTP save (student token)
     └───────────────┴───────────────┴──────┬─────────┴──────────────────┴──────────────────┘  └─▶ student service
                                            ▼                                                     Ollama qwen3:8b
                                 MongoDB p4_handshake (GridFS for resumes/pictures)
                                            ▲
     Kafka (KRaft) p4.* topics + .dlq ──▶ workers: application, notification, event, job (search index), memory
```

| Service | Image | Routes | Publishes |
|---|---|---|---|
| Student | `p4-student-service:2.0` | `/auth/*`, `/students`, `/preferences`, `/saved`, `/uploads/pictures` | — |
| Company | `p4-company-service:2.0` | `/auth/company/signup`, `/employer/profile` | — |
| Job | `p4-job-service:2.0` | `/jobs`, `/employer/jobs` | `p4.job.created` |
| Application | `p4-application-service:2.0` | `/applications`, `/employer/applications` | `p4.application.created`, `.updated`, `.status_changed` |
| Event | `p4-event-service:2.0` | `/events`, `/employer/events` | `p4.event.registration_created` |
| AI Assistant | `p4-assistant-service:2.0` | `/assistant/*` | `p4.assistant.interaction`, `p4.assistant.memory_consolidate` |

| Topic | Producer | Consumer (worker) |
|---|---|---|
| `p4.application.created` / `p4.application.updated` | Application API | application worker (writes the application) |
| `p4.application.status_changed` | Application API (company PATCH) | notification worker |
| `p4.event.registration_created` | Event API | event worker (writes the registration) |
| `p4.job.created` | Job API | job worker (search terms index) |
| `p4.assistant.interaction` | Assistant API | memory worker (learns memory entries) |
| `p4.assistant.memory_consolidate` | Assistant `/memory consolidate` | memory worker (consolidation) |
| `<topic>.dlq` | any worker after 3 failed attempts | — (inspected; also stored in `dead_letters`) |

All services share one code base (`backend/app`); `app/services/<name>.py`
mounts only that service's routers. `app.main` mounts all of them in one
process for local development and the tests.

## Running locally with Docker Compose

Prerequisites: Docker, and [Ollama](https://ollama.com) on the host with
`ollama pull qwen3:8b`. Copy `.env.example` to `.env` and set
`MONGO_PASSWORD` and `JWT_SECRET_KEY` (`.env` is git-ignored).

```bash
docker compose up -d --build                     # build and start 15 containers
docker compose ps                                # health of every service
backend/.venv/bin/python database/seed/generate_seed.py --reset   # seed MongoDB (host port 27047)
open http://localhost:9040                       # frontend + API gateway (/api/*)
docker compose logs -f p4-application-worker     # watch a Kafka consumer
docker compose down                              # stop (add -v to delete the data volume)
```

The seed script needs the backend virtualenv once:
`python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt`.

Check the paths the lab asks for: the frontend reaches the backend
(`curl localhost:9040/api/jobs`), the backend reaches MongoDB
(`curl localhost:9041/health/ready`), and the assistant reaches the
platform services and the model
(`docker exec p4-assistant-service python -c "import urllib.request as u;print(u.urlopen('http://p4-student-service:9041/health').read())"`).

### Demo accounts

Every seeded account uses the password `Pair4Demo!`.

| Account | Email | Notes |
|---|---|---|
| Student | `demo.student@example.edu` | San Jose, saved preferences, 64 memory entries |
| Student | `noprefs.student@example.edu` | no saved preferences |
| Company | `demo.company@example.com` | TechNova Solutions |

## Kubernetes

Manifests are in `k8s/base` (namespace `p4-handshake`, ConfigMap, MongoDB
and Kafka StatefulSets, a topic-creation Job, six service Deployments with
ClusterIP Services, five worker Deployments, the frontend with a
LoadBalancer Service, HPAs). `k8s/base/02-secret.example.yaml` is only a
template: the real Secret is created from `.env` by `scripts/k8s_secrets.sh`.

Local cluster (kind), as used for the evidence in `docs/evidence/k8s_local_kind.txt`:

```bash
kind create cluster --config k8s/kind-cluster.yaml
docker compose build
kind load docker-image p4-student-service:2.0 p4-company-service:2.0 p4-job-service:2.0 \
  p4-application-service:2.0 p4-event-service:2.0 p4-assistant-service:2.0 p4-frontend:2.0 --name p4-handshake
./scripts/k8s_secrets.sh
kubectl apply -k k8s/overlays/local
kubectl -n p4-handshake get pods,svc
open http://localhost:9050                       # NodePort mapped by kind-cluster.yaml
```

### AWS (ECR + EKS)

```bash
eksctl create cluster -f k8s/eks-cluster.yaml    # p4-handshake, us-west-2
./scripts/aws_push_ecr.sh                        # build linux/amd64 images, push p4-*:2.0 to ECR
ECR_REGISTRY=<account>.dkr.ecr.us-west-2.amazonaws.com ./scripts/aws_deploy_eks.sh
./scripts/aws_pause.sh pause                     # scale node groups to 0 after collecting evidence
./scripts/aws_pause.sh resume                    # bring it back for the demo
```

**Deployed 2026-11-16** to EKS cluster `p4-handshake` (us-west-2) with the
seven `p4-*` images (tag `2.0`) in ECR. The account's EC2 quota is 5 vCPUs,
so the cluster is one `m7i.xlarge` node and the `aws` overlay runs
`qwen3:1.7b` (an assistant answer takes about 3 minutes there; see the
report, section 4.4). Evidence: `docs/evidence/aws_*.txt` and
`docs/report/lab2/screenshots/aws_*`.

**Accessing the AWS deployment.** After `./scripts/aws_pause.sh resume`
(or a fresh deploy), the public address is the frontend LoadBalancer:

```bash
kubectl -n p4-handshake get svc p4-frontend \
  -o jsonpath='http://{.status.loadBalancer.ingress[0].hostname}:9040{"\n"}'
```

Open that address and sign in with a demo account below. The Kubernetes
console views in the AWS console need an EKS access entry for the console
user; `kubectl` (as the IAM user that created the cluster) shows everything.

## Kafka failure cases

```bash
./scripts/kafka_failure_demos.sh                 # against the cluster; output in docs/evidence/kafka_failures.log
```

Duplicates are skipped (event_id idempotency + unique keys), a worker
killed mid-message reprocesses it (offsets are committed only after the
database write), and a poison message goes to `<topic>.dlq` after three
attempts while later messages keep flowing. Details: `RUN_LOG.txt`.

## AI assistant

Use it in the web app (student sidebar → AI Assistant) or from the
terminal (`backend/.venv/bin/python backend/scripts/assistant_cli.py`).

- **Memory:** rules (`assistant_rules`), learned memory (`student_memory`,
  one `date | category | description` entry per fact), and the session
  (`assistant_sessions`, expires after 4 hours). Commands: `/memory`,
  `/memory add <category>: <fact>`, `/memory consolidate`, `/memory rules`,
  `/memory clear`.
- **Tokens and compaction:** each answer reports prompt/completion tokens
  and the percentage of the 12,288-token context; the UI warns above 70%.
  `/compact` (or 60% of the window) replaces the history with a summary.
- **Tracing:** every request has a `trace_id` (`X-Trace-Id`) carried into
  Kafka headers and worker logs; stage timings are stored in `traces`.

| Requirement | Where |
|---|---|
| Agent loop, iteration ceiling, timeout, tool-retry bound, redaction | `backend/app/assistant/agent.py` |
| Tools, schemas, allowlist, untrusted-data fencing | `backend/app/assistant/tools.py` |
| Confirmation gate | `backend/app/assistant/confirm.py` |
| Guardrail overview and redaction | `backend/app/assistant/guardrails.py` |
| Memory layers, `/memory`, consolidation consumer | `backend/app/assistant/memory.py` |
| Compaction and token usage | `backend/app/assistant/compaction.py` |
| HTTP endpoints | `backend/app/assistant_routes.py` |

### Guardrail harness (one command)

```bash
cd backend && KAFKA_ENABLED=false .venv/bin/python -m harness.agent_harness
```

Runs 16 cases with a deterministic model through the production loop,
validation, confirmation, authorization, and tool code; writes
`docs/evaluation/agent_harness.json` and `agent_harness.md`.

### Tests

```bash
docker compose up -d p4-mongo
cd backend && KAFKA_ENABLED=false .venv/bin/python -m pytest -q
```

## Performance testing (JMeter)

```bash
./loadtest/run_loadtest.sh                        # CRUD at 100..500 users, assistant at 5..50
backend/.venv/bin/python loadtest/analyze_results.py   # summary.md + graphs in loadtest/results/
```

The plan is `loadtest/p4_handshake.jmx` (generated by `loadtest/build_plan.py`).

## Repository layout

```
backend/app/              FastAPI code shared by all services (routes, security, messaging, observability)
backend/app/services/     one FastAPI app per service + factory (health, tracing middleware)
backend/app/workers/      Kafka consumer runner, handlers, failure-case demo
backend/app/assistant/    agent loop, tools, confirmation, guardrails, memory, compaction, model client
backend/docker/           one Dockerfile per service
backend/harness/          deterministic guardrail harness
backend/scripts/          assistant CLI, evaluations, compaction and trace evidence
backend/tests/            pytest suite
database/seed/            seed generator, MongoDB loader, memory fixture, injection fixture
database/legacy_mysql/    the Lab 1 MySQL schema (for reference)
frontend/src/store/       Redux store and slices
frontend/docker/          frontend Dockerfile and nginx gateway template
k8s/                      base manifests, local (kind) and AWS overlays, EKS config
loadtest/                 JMeter plan, data prep, runner, results
infra/kafka/              topic creation script
scripts/                  Kubernetes secret, Kafka failure demos, AWS push/deploy/pause
docs/                     API docs, evaluation output, evidence, report
METRICS.md  RUN_LOG.txt  AI_USE.md
```
