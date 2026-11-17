"""
Kafka consumer loop shared by every worker.

    python -m app.workers.runner application   # application.created / updated
    python -m app.workers.runner notification  # application.status_changed
    python -m app.workers.runner event         # event.registration_created
    python -m app.workers.runner job           # job.created
    python -m app.workers.runner memory        # assistant interaction + consolidation

Delivery rules:
- enable.auto.commit is off. The offset is committed only after the
  database write succeeded (or the message was parked in the DLQ), so a
  worker killed mid-message reprocesses it after restart; idempotent
  handlers make that safe.
- A message that fails is retried MAX_ATTEMPTS times with backoff. If it
  still fails it is a poison message: it is published to <topic>.dlq,
  recorded in the dead_letters collection, and its offset is committed so
  the partition keeps moving.
"""

import json
import os
import signal
import sys
import time

from confluent_kafka import Consumer, KafkaError

from .. import messaging
from ..database import ensure_indexes, get_database, utcnow
from ..observability import log_event, record_stage, reset_trace_id, set_trace_id
from .handlers import WORKER_TOPICS, process


MAX_ATTEMPTS = int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))
BACKOFF_SECONDS = float(os.getenv("WORKER_BACKOFF_SECONDS", "0.5"))

_running = True


def _stop(*_):
    global _running
    _running = False


def _header(message, name: str) -> str | None:
    for key, value in message.headers() or []:
        if key == name and value:
            return value.decode()
    return None


def _decode(raw: bytes) -> dict:
    message = json.loads(raw)
    if not isinstance(message, dict) or "event_id" not in message or "payload" not in message:
        raise ValueError("message is not a Handshake event envelope")
    return message


def _dead_letter(db, kafka_message, error: str, attempts: int, trace_id: str | None) -> None:
    topic = kafka_message.topic()
    raw = kafka_message.value() or b""

    messaging.publish_raw(
        messaging.dlq(topic),
        (kafka_message.key() or b"").decode(errors="replace"),
        json.dumps({
            "original_topic": topic,
            "partition": kafka_message.partition(),
            "offset": kafka_message.offset(),
            "error": error,
            "attempts": attempts,
            "raw": raw.decode(errors="replace"),
        }).encode(),
        trace_id,
    )

    db.dead_letters.insert_one({
        "topic": topic,
        "partition": kafka_message.partition(),
        "offset": kafka_message.offset(),
        "key": (kafka_message.key() or b"").decode(errors="replace"),
        "raw": raw.decode(errors="replace")[:2000],
        "error": error,
        "attempts": attempts,
        "trace_id": trace_id,
        "failed_at": utcnow(),
    })


def handle_message(db, kafka_message) -> str:
    """
    Decode, process with bounded retries, or park in the DLQ.
    Returns "processed", "duplicate_skipped", or "dead_lettered".
    """

    topic = kafka_message.topic()
    trace_id = _header(kafka_message, "trace_id")
    last_error = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.perf_counter()
        try:
            message = _decode(kafka_message.value())
            trace_id = message.get("trace_id") or trace_id
            tokens = set_trace_id(trace_id, bool(message.get("sampled")))

            try:
                # Time between publish and this worker picking it up.
                _, produced_ms = kafka_message.timestamp()
                queue_ms = max(0.0, time.time() * 1000 - produced_ms) if attempt == 1 else 0.0
                if attempt == 1:
                    record_stage("kafka.queue_wait", queue_ms, topic=topic)

                outcome = process(db, topic, message)
                record_stage("worker.process", (time.perf_counter() - started) * 1000, topic=topic, outcome=outcome)
            finally:
                reset_trace_id(tokens)

            log_event("message handled", topic=topic, partition=kafka_message.partition(),
                      offset=kafka_message.offset(), outcome=outcome, attempt=attempt, trace_id=trace_id)
            return outcome

        except Exception as error:  # noqa: BLE001 - every failure is retried, then DLQ'd
            last_error = f"{type(error).__name__}: {error}"
            log_event("message failed", topic=topic, offset=kafka_message.offset(),
                      attempt=attempt, max_attempts=MAX_ATTEMPTS, error=last_error, trace_id=trace_id)
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS * (2 ** (attempt - 1)))

    _dead_letter(db, kafka_message, last_error, MAX_ATTEMPTS, trace_id)
    log_event("moved to dead-letter topic", topic=topic, dlq=messaging.dlq(topic),
              offset=kafka_message.offset(), error=last_error, trace_id=trace_id)
    return "dead_lettered"


def run(worker: str) -> None:
    topics = WORKER_TOPICS[worker]
    db = get_database()
    ensure_indexes(db)

    consumer = Consumer({
        "bootstrap.servers": messaging.bootstrap_servers(),
        "group.id": f"{messaging.PREFIX}-{worker}-worker",
        "client.id": f"{messaging.PREFIX}-{worker}-worker-{os.getenv('HOSTNAME', 'local')}",
        "enable.auto.commit": False,
        "auto.offset.reset": "earliest",
        "max.poll.interval.ms": 600000,
    })
    consumer.subscribe(topics)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    log_event("worker started", worker=worker, topics=topics, group=f"{messaging.PREFIX}-{worker}-worker")

    try:
        while _running:
            kafka_message = consumer.poll(1.0)
            if kafka_message is None:
                continue
            if kafka_message.error():
                if kafka_message.error().code() != KafkaError._PARTITION_EOF:
                    log_event("consumer error", error=str(kafka_message.error()))
                continue

            handle_message(db, kafka_message)
            # Commit only after the database write (or the DLQ hand-off).
            consumer.commit(message=kafka_message, asynchronous=False)
            log_event("offset committed", topic=kafka_message.topic(),
                      partition=kafka_message.partition(), offset=kafka_message.offset() + 1)
    finally:
        consumer.close()
        log_event("worker stopped", worker=worker)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in WORKER_TOPICS:
        sys.exit(f"usage: python -m app.workers.runner {{{'|'.join(WORKER_TOPICS)}}}")
    run(sys.argv[1])
