"""
utils/relevance_scorer.py

RelevanceScorer: Async and Sync Application for reward/penalty and decayed scoring logic to document nodes,
and persists updates to Neo4j.
Async-First architecture

Usage:
    async def handle_query_async():
        scorer = RelevanceScorer()
        metadata = {"clause_id": "123", "score": 0.5}
        await scorer.areward(metadata)

    def handle_query_sync():
        scorer = RelevanceScorer()
        metadata = {"clause_id": "123", "score": 0.5}
        scorer.reward(metadata)  # Async persistence in background
"""

import math
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import asyncio
import threading

from neo4j import AsyncDriver, Driver
from neo4j.exceptions import Neo4jError

from .logger import get_logger
from .neo4j_utils import get_neo4j_config, get_neo4j_driver, get_async_neo4j_driver

logger = get_logger("jsentrix")


class RelevanceScorer:
    """
    Hybrid scoring, rewarding/penalizing of document nodes  with persistence to Neo4j
    supporting both sync and async execution patterns.

    Uses async Neo4j driver under the hood with automatic sync fallback.

    Features:
    - Score decay based on document age
    - Reward/penalty system with persistence in neo4j
    - Thread-safe async operations
    - Automatic connection pooling
    """

    def __init__(
        self,
        base_score: float = 0.8,
        decay_rate: float = 0.05,
        reward_amount: float = 0.1,
        penalty_amount: float = 0.05,
        neo4j_config: Dict[str, str] = None,
        sync_driver: Optional[Driver] = None,
        async_driver: Optional[AsyncDriver] = None,
    ):
        self.base_score = base_score
        self.decay_rate = decay_rate
        self.reward_amount = reward_amount
        self.penalty_amount = penalty_amount
        self.neo4j_config = neo4j_config or get_neo4j_config()

        # initialize drivers
        self.sync_driver = sync_driver or get_neo4j_driver()
        self.async_driver = async_driver or get_async_neo4j_driver()

    async def _apersist_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Persists updated score and access timestamp back to Neo4j.
        Core async persistance with connection pooling and retries
        """
        if not (clause_id := metadata.get("clause_id")):
            logger.error("Missing clause_id. Skipping Neo4j update.")
            return

        label = self.neo4j_config["node_label"]
        query = f"""
        MATCH (n:{label} {{clause_id: $clause_id}})
        SET n.score = $score, n.last_accessed_at = $last_accessed_at
        """
        params = {
            "clause_id": clause_id,
            "score": metadata["score"],
            "last_accessed_at": metadata.get("last_accessed_at"),
        }

        try:
            async with self.async_driver.session() as session:
                await session.execute_write(lambda tx: tx.run(query, params))
            logger.debug(f"Updated clause {clause_id} scores in Neo4j.")
        except Neo4jError as e:
            logger.error(f"Neo4j persistance failed: {e.message}")

    def score(self, metadata: Dict[str, Any]) -> float:
        """
        Computes the final decayed relevance score for a document (pure function no I/O)

        Args:
            metadata: Document metadata containing:
                - score: Original similarity score
                - last_accessed_at: ISO timestamp string

        Returns:
            float: Adjusted score between 0.0 and 1.0
        """
        score = metadata.get("score", self.base_score)

        last_accessed_at = metadata.get("last_accessed_at")
        logger.debug(
            f"Scoring: clause_id={metadata.get('clause_id')}, original_score={score}, last_accessed_at={last_accessed_at}, decay_rate={self.decay_rate}"
        )
        if last_accessed_at:
            try:
                dt = datetime.fromisoformat(last_accessed_at)
                age_days = (datetime.now(timezone.utc) - dt).days
                age_days = max(age_days, 0)  # Prevent negative decay
                score *= math.exp(-self.decay_rate * age_days)
            except Exception as e:
                logger.debug(f"Error in score decay: {str(e)}")
        logger.debug(f"decayed_score={score}")
        return min(max(score, 0.0), 1.0)

    async def areward(self, metadata: Dict[str, Any]) -> None:
        """
        Async reward with immediate persistance.

        Args:
            metadata: Document metadata to update
        """
        metadata["score"] = min(
            metadata.get("score", self.base_score) + self.reward_amount, 1.0
        )
        metadata["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
        await self._apersist_metadata(metadata)

    def _run_async_persist_in_thread(self, metadata: Dict[str, Any]):
        asyncio.run(self._apersist_metadata(metadata))

    def _fire_and_forget_async_persist(self, metadata: Dict[str, Any]):
        """
        Schedules async persistence in the correct context.
        - If in an async context, uses asyncio.create_task.
        - If in a sync context, starts a background thread with its own event loop.
        """
        try:
            loop = asyncio.get_running_loop()
            # If this succeeds, we're in an async context
            loop.create_task(self._apersist_metadata(metadata))
        except RuntimeError:
            # No running event loop; run in a background thread with its own event loop
            threading.Thread(
                target=self._run_async_persist_in_thread, args=(metadata,), daemon=True
            ).start()

    def reward(self, metadata: Dict[str, Any]) -> None:
        """
        Rewards a document by increasing its score and updating access time.
        with fire-and-forget async persistance (never blocking sync code)
        """
        score = metadata.get("score", self.base_score)
        score = min(score + self.reward_amount, 1.0)
        metadata["score"] = score
        metadata["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
        logger.debug(
            f"Document {metadata.get('clause_id')} rewarded. New score: {score}"
        )
        self._fire_and_forget_async_persist(metadata)

    async def apenalize(self, metadata: Dict[str, Any]) -> None:
        """
        Async penalty with immediate persistance

        Args:
            metadata: Document metadata to update
        """
        metadata["score"] = max(
            metadata.get("score", self.base_score) - self.penalty_amount, 0.0
        )
        await self._apersist_metadata(metadata)

    def penalize(self, metadata: Dict[str, Any]) -> None:
        """
        Penalizes a document by decreasing its score.
        Sync penalty with fire and forget async persistance
        """
        score = metadata.get("score", self.base_score)
        score = max(score - self.penalty_amount, 0.0)
        metadata["score"] = score
        logger.debug(
            f"Document {metadata.get('clause_id')} penalized. New score: {score}"
        )
        self._fire_and_forget_async_persist(metadata)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sync_driver.close()
        # async driver cleaner is managed via context mangagers

    async def aclose(self):
        "Async cleanup method"
        await self.async_driver.close()
