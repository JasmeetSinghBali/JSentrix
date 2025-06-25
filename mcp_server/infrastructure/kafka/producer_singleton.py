"""
mcp_server/infrastructure/kafka/producer_singleton.py

Asyncio-friendly, singleton Kafka producer for MCP server.

Features:
- Singleton instance for process-wide reuse
- Thread-safe lazy initialization
- Tenacity-based automatic retries with exponential backoff
- Background poll thread for delivery callbacks
- Async produce method returns awaitable Future
"""

import json
import asyncio
from threading import Lock, Thread
from utils.logger import get_logger
from confluent_kafka import Producer, KafkaException
from tenacity import retry, wait_exponential, stop_after_attempt

logger = get_logger("mcp_server_producer_kafka")


class AsyncKafkaProducer:
    def __init__(self, bootstrap_servers: str):
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "message.send.max.retries": 5,
                "retry.backoff.ms": 1000,
                "queue.buffering.max.messages": 100000,
                "compression.type": "snappy",
            }
        )
        self._cancelled = False
        self._poll_thread = Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        logger.info(f"Kafka producer initialized for {bootstrap_servers}")

    def _poll_loop(self):
        while not self._cancelled:
            self._producer.poll(0.1)

    def close(self):
        self._cancelled = True
        self._poll_thread.join()
        self._producer.flush(10)
        logger.info("Kafka producer closed")

    @retry(
        wait=wait_exponential(multiplier=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def produce(self, topic: str, event: dict) -> None:
        """
        Async produce event to Kafka topic with robust retry logic.

        Args:
            topic: Kafka topic name
            event: Event payload as dict
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        value = json.dumps(event).encode("utf-8")

        def ack(err, msg):
            # 📌 guard for future is already completed
            def complete():
                if future.done():
                    return  # Prevent InvalidStateError
                if err:
                    future.set_exception(KafkaException(err))
                else:
                    future.set_result(msg)

            loop.call_soon_threadsafe(complete)

        try:
            self._producer.produce(topic=topic, value=value, on_delivery=ack)
        except KafkaException as e:
            logger.error(f"Kafka produce error: {e}")
            raise

        await future  # Await delivery confirmation


# --- Singleton logic ---

_kafka_producer_instance = None
_kafka_producer_lock = Lock()


def get_kafka_producer(bootstrap_servers: str):
    global _kafka_producer_instance
    if _kafka_producer_instance is None:
        with _kafka_producer_lock:
            if _kafka_producer_instance is None:
                _kafka_producer_instance = AsyncKafkaProducer(bootstrap_servers)
    return _kafka_producer_instance


import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
kafka_producer = get_kafka_producer(KAFKA_BOOTSTRAP_SERVERS)
