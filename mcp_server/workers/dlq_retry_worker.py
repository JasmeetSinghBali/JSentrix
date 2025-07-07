"""
mcp_server/workers/dlq_retry_worker.py

Kafka DLQ retry background worker.
- Consumes from DLQ_TOPIC and retries original_event to ORIGINAL_TOPIC.
- If retries exceed max, sends to RETRY_DLQ_TOPIC.
"""

import asyncio
import json
import os
from typing import Optional

from confluent_kafka import Consumer, KafkaException
from infrastructure.kafka.producer_singleton import kafka_producer
from utils.logger import get_logger
from utils.background_worker import background_worker

logger = get_logger("dlq_retry_worker")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
DLQ_TOPIC = "ingest_topic_dlq"
RETRY_DLQ_TOPIC = "ingest_topic_dlq_retry"
ORIGINAL_TOPIC = "ingest_topic"
MAX_RETRY_ATTEMPTS = 3

KAFKA_CONFIG = {
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
    "group.id": "dlq-retry-consumer-group",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
}


def get_consumer():
    return Consumer(KAFKA_CONFIG)


async def resend_event(event: dict|str, topic: str):
    try:
        if isinstance(event,str):
            try:
                # convert stringified dict back to dict
                event = json.loads(event)
            except json.JSONDecodeError:
                logger.warning("⚠️ Event is string but not JSON — wrapping it.")
                event = {
                    "event": "log",
                    "message": f"unparseable: {event}",
                    "stream_id": "unknown"
                }
        # 📌 Deep clean: ensure all values are JSON-safe (e.g., <object at ...> -> str)
        from infrastructure.ingestion.forwarder import make_serializable
        event = make_serializable(event)

        logger.debug(f"📦 Re-Sending event to Kafka: {json.dumps(event)}")
        await kafka_producer.produce(topic, event)
        logger.info(f" ✅ Successfully resent event to topic {topic}")
        return True
    except KafkaException as e:
        logger.error(f" ❌ Kafka resend failed: {e}")
        return False


def extract_retry_count(dlq_payload: dict) -> int:
    return dlq_payload.get("retry_attempts", 0)

@background_worker(name="DLQRetryWorker", retry=True, max_retries=-1, backoff_base=2.0)
async def dlq_background_retry_loop():
    consumer = get_consumer()
    consumer.subscribe([DLQ_TOPIC])
    logger.info(f"🔁 DLQ retry consumer subscribed to {DLQ_TOPIC}")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                await asyncio.sleep(0.25)
                continue
            if msg.error():
                logger.error(f"DLQ message error: {msg.error()}")
                continue

            try:
                payload = json.loads(msg.value().decode("utf-8"))
                original_event = payload.get("original_event")
                if not original_event:
                    logger.warning("Missing original_event in DLQ payload")
                    continue

                retry_attempts = extract_retry_count(payload) + 1
                payload["retry_attempts"] = retry_attempts

                if retry_attempts > MAX_RETRY_ATTEMPTS:
                    logger.warning(f"Exceeded max retries, sending to {RETRY_DLQ_TOPIC}")
                    await resend_event(payload, RETRY_DLQ_TOPIC)
                    consumer.commit(msg)
                    continue

                success = await resend_event(original_event, ORIGINAL_TOPIC)
                if success:
                    consumer.commit(msg)

            except Exception as e:
                logger.exception(f"❗ Unexpected error while processing DLQ message: {e}")
    
    finally:
        consumer.close()
        logger.info("🛑 DLQ Kafka consumer closed cleanly")