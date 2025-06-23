"""
mcp_server/infrastructure/kafka/topic_initializer.py

creation ingest_topic and ingest_topic_dlq topic at startup before subscriber of dlq bg worker setup
"""

from confluent_kafka.admin import AdminClient, NewTopic
from utils.logger import get_logger

logger = get_logger("kafka_topic_initializer")


def ensure_kafka_topics_exist(bootstrap_servers: str, topic_names: list[str]):
    admin_client = AdminClient({"bootstrap.servers": bootstrap_servers})
    existing_topics = admin_client.list_topics(timeout=10).topics

    to_create = [
        NewTopic(name, num_partitions=1, replication_factor=1)
        for name in topic_names
        if name not in existing_topics
    ]

    if not to_create:
        logger.info("✅ All Kafka topics already exist.")
        return

    futures = admin_client.create_topics(to_create)

    for topic, future in futures.items():
        try:
            future.result()
            logger.info(f"✅ Created topic: {topic}")
        except Exception as e:
            logger.error(f"❌ Failed to create topic {topic}: {e}")
