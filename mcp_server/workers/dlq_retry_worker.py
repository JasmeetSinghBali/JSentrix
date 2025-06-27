"""
mcp_server/workers/dlq_retry_worker.py
"""

import asyncio
import json
import os
from typing import Optional

from confluent_kafka import Consumer, KafkaException
from infrastructure.kafka.producer_singleton import kafka_producer
from utils.logger import get_logger
from utils.lifecycle import register_shutdown_callback

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

# register background loop and its shutdown cancelation
_dlq_task = None

async def dlq_background_retry_loop():
    global _dlq_task
    consumer = get_consumer()
    consumer.subscribe([DLQ_TOPIC])
    logger.info(f"🔁 DLQ retry consumer subscribed to {DLQ_TOPIC}")

    async def worker_loop():
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
    
    # spawn task and register cleanup
    _dlq_task = asyncio.create_task(worker_loop())

    async def stop_dlq_task():
        if _dlq_task:
            _dlq_task.cancel() # only marks it as cancelled
            try:
                await _dlq_task # actually executes the cancellation of the task by explicit throwing off CancelledError for clean cancellation
            except asyncio.CancelledError:
                logger.info("🛑 DLQ retry task shutdown cleanly")
    
    register_shutdown_callback(stop_dlq_task)