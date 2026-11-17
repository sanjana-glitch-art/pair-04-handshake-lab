### Test conditions

Everything ran on one Apple M4 laptop (10 cores, 16 GB): the Compose stack
(each service runs 2 uvicorn workers; FastAPI runs sync endpoints in a
40-thread pool per worker), MongoDB, Kafka, Ollama, *and* JMeter with up
to 500 threads. Each CRUD user signs in or searches 5–20 times after a
2-second ramp, so all N users are active together. The laptop suspended
a few times during the long runs (gaps of 700–1,060 s with no request in
flight; no single request took longer than 11 s), so throughput is
computed over active time: idle gaps longer than 30 s are removed
(`analyze_results.py`). Throughput numbers on a shared laptop are noisy
(±30% between repeated runs); the latency trends are the reliable signal.

### What limits each endpoint

**Login — the first bottleneck (CPU, bcrypt).** Every sign-in verifies a
bcrypt hash (cost 10 for seeded users, about 50–60 ms of pure CPU) and
writes a session and an activity-log document. During the 100-user run the
student service container used ~860% CPU. Throughput stops growing after
about 200 users (41 → 71 req/s, then 44–62 req/s) while average latency
rises almost linearly with concurrency (1.1 s → 5.3 s; p95 2.0 s → 9.2 s):
extra users only wait longer in the thread-pool queue for a CPU core.
This is Little's law: with throughput fixed at roughly 50–60 sign-ins/s,
N users in flight wait about N / 55 seconds. bcrypt is deliberately slow,
so the fix is more student-service CPU (more replicas — the HPA targets
70% CPU), not a cheaper hash.

**Job search and event search — database and serialization.** A search
is one indexed MongoDB query plus JSON encoding of up to a few hundred
documents. Averages stay below 1 s up to 500 users (job search 0.29 →
0.86 s, event search 0.08–0.90 s) with no errors; throughput peaks around
600–800 req/s and then levels off as the two uvicorn workers, MongoDB, and
JMeter itself compete for the same CPU. Event search also computes
eligibility per event for the signed-in student, which is why its latency
grows at 300+ users.

**Application submission — fast because Kafka absorbs the write.** The
API validates the request, stores the resume in GridFS, publishes
`application.created`, and answers 202. The database insert happens in the
application worker, outside the request. Average response time stays
between 45 and 375 ms at every level. The final runs returned 1,500
`202` responses; afterwards the `p4-application-worker` group had lag 0 on
all three partitions and `dead_letters` was empty, so every queued
submission was consumed and written. The extra latency at 200 and 500
users comes from GridFS writes and the producer flush (`acks=all`) sharing
CPU with the 500 JMeter threads; the workers were never the limit.

### Bottleneck order

1. CPU for bcrypt sign-ins (student service) — saturates first, ~200 users.
2. Shared CPU between the API workers, MongoDB, and the load generator —
   search latency grows from 300 users.
3. Kafka and the workers were never the limit for these rates.

### Assistant endpoint: model inference is the bottleneck

The assistant behaves completely differently from the CRUD endpoints.
One answer needs 2–3 calls to qwen3:8b with reasoning on; the traces
(section 9.3) put the median request at about 55 s, 99.9% of it in model
inference. Ollama on this laptop serves **one generation at a time**
(`-np 1`), so concurrent chats do not run in parallel. They wait in
Ollama's queue, and the k-th user in line waits roughly k × 50 s before
its own first call even starts.

- **5 users:** all 5 answered, but p50 is 295 s and p99 366 s. Almost all of
  that is queue wait, not work.
- **10 users:** only 1 of the 6 traced requests answered. The rest hit the
  model client's 300 s HTTP timeout (`model_error`) or the 240 s request
  deadline (`timeout`); 4 requests left no trace because the laptop
  suspended during that run.
- **20 and 50 users:** 0 answered. Every request either timed out waiting
  for the model or ran out of its request deadline. Latency flattens at
  about 300–510 s because the timeouts cap it, not because the system got
  faster.

The guardrail-7 limits did their job: requests failed with an explicit
"the assistant model is not available right now" answer instead of
hanging the gateway (nginx allows 600 s), and the CRUD services stayed
responsive throughout because the model runs outside them.

**CRUD vs assistant.** A CRUD request costs milliseconds of database work
and a little CPU, and its capacity scales with API replicas and MongoDB.
An assistant request costs tens of seconds of GPU/CPU inference, and its
capacity is the number of parallel model slots: here one slot, about
1 request per 50 s (≈ 0.02 req/s), about four orders of magnitude below
job and event search (400–800 req/s). Queueing theory says the same: with a service time of ~50 s,
any arrival rate above 0.02 req/s makes the queue grow without bound, so
latency rises until requests hit a timeout. Adding API pods does nothing
for this. It needs more model capacity (`OLLAMA_NUM_PARALLEL`, a GPU node,
more Ollama replicas behind the service), fewer calls per answer
(reasoning off: median 34–36 s per turn vs 73–117 s with reasoning on in
Lab 1's METRICS.md, about 2–3× faster), or admission
control that rejects early with a "busy, try again" message instead of
queueing for 300 s.

**Measurement note.** The assistant returns HTTP 200 even when the model
failed, so JMeter's own error rate was 0%. The error rates above count
every request that did not end with an answer, from the per-request
status stored in the traces. The plan now has a JSON assertion
(`$.status` must be `final` or `confirmation_required`) so future runs
report these as errors directly.
