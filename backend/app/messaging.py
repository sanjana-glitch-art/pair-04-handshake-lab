"""
Kafka producer side.

APIs call publish(topic, key, payload). Each message is a JSON envelope
with a unique event_id (used by consumers for idempotency), the event
type, a timestamp, and the trace_id of the request that produced it.
The trace_id is also sent as a Kafka header.

When KAFKA_ENABLED=false (unit tests, or running one service by hand
without Kafka) the matching worker handler runs in-process instead, so
the same code path writes the database either way.
"""

import json
import os
import threading
import time
from uuid import uuid4

from .database import utcnow
from .observability import current_trace_id, is_sampled, log_event, record_stage


PREFIX = os.getenv("KAFKA_TOPIC_PREFIX", os.getenv("DB_PREFIX", "p4"))


def topic(name: str) -> str:
    return f"{PREFIX}.{name}"


APPLICATION_CREATED = topic("application.created")
APPLICATION_UPDATED = topic("application.updated")
APPLICATION_STATUS_CHANGED = topic("application.status_changed")
EVENT_REGISTRATION_CREATED = topic("event.registration_created")
JOB_CREATED = topic("job.created")
ASSISTANT_INTERACTION = topic("assistant.interaction")
MEMORY_CONSOLIDATE = topic("assistant.memory_consolidate")

ALL_TOPICS = [
    APPLICATION_CREATED,
    APPLICATION_UPDATED,
    APPLICATION_STATUS_CHANGED,
    EVENT_REGISTRATION_CREATED,
    JOB_CREATED,
    ASSISTANT_INTERACTION,
    MEMORY_CONSOLIDATE,
]


def dlq(topic_name: str) -> str:
    return f"{topic_name}.dlq"


def kafka_enabled() -> bool:
    return os.getenv("KAFKA_ENABLED", "true").lower() == "true"


def bootstrap_servers() -> str:
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9047")


_producer = None
_producer_lock = threading.Lock()


def get_producer():
    global _producer

    if _producer is None:
        with _producer_lock:
            if _producer is None:
                from confluent_kafka import Producer

                _producer = Producer({
                    "bootstrap.servers": bootstrap_servers(),
                    "client.id": os.getenv("SERVICE_NAME", "handshake"),
                    # Idempotent producer: retries never write a message twice.
                    "enable.idempotence": True,
                    "acks": "all",
                    "linger.ms": 5,
                    "message.timeout.ms": 10000,
                })

    return _producer


def envelope(event_type: str, payload: dict, event_id: str | None = None, trace_id: str | None = None) -> dict:
    return {
        "event_id": event_id or uuid4().hex,
        "type": event_type,
        "occurred_at": utcnow().isoformat() + "Z",
        "trace_id": trace_id or current_trace_id(),
        "sampled": is_sampled(),
        "payload": payload,
    }


class PublishError(Exception):
    pass


def publish_raw(topic_name: str, key: str, value: bytes, trace_id: str | None = None, wait: bool = True) -> None:
    """
    Sends bytes as-is. Used by publish() and by the poison-message demo.
    """

    producer = get_producer()
    errors: list[str] = []

    def on_delivery(error, message):
        if error is not None:
            errors.append(str(error))

    headers = [("trace_id", (trace_id or "").encode())] if trace_id else None
    producer.produce(topic_name, key=key.encode(), value=value, headers=headers, on_delivery=on_delivery)

    if wait:
        remaining = producer.flush(10)
        if remaining or errors:
            raise PublishError(errors[0] if errors else "Kafka did not acknowledge the message in time.")
    else:
        producer.poll(0)


def publish(topic_name: str, key: str, payload: dict, event_id: str | None = None, wait: bool = True) -> dict:
    """
    Publishes one event and returns its envelope. With Kafka disabled,
    runs the consumer's handler directly.
    """

    message = envelope(topic_name.split(".", 1)[-1], payload, event_id=event_id)
    started = time.perf_counter()

    if not kafka_enabled():
        from .workers.handlers import handle_inline

        handle_inline(topic_name, message)
        record_stage("kafka.inline_handler", (time.perf_counter() - started) * 1000, topic=topic_name)
        return message

    publish_raw(topic_name, key, json.dumps(message).encode(), message["trace_id"], wait=wait)
    elapsed = (time.perf_counter() - started) * 1000
    record_stage("kafka.publish", elapsed, topic=topic_name, key=key)
    log_event("published", topic=topic_name, key=key, event_id=message["event_id"])

    return message
