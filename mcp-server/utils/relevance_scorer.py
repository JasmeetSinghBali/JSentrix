import math
from typing import Dict, Any
from datetime import datetime, timezone
from neo4j import GraphDatabase
from utils.logger import get_logger
from utils.neo4j_utils import get_neo4j_config 

logger = get_logger("jsentrix")

class RelevanceScorer:
    def __init__(
        self,
        base_score: float = 0.8,
        decay_rate: float = 0.05,
        reward_amount: float = 0.1,
        penalty_amount: float = 0.05,
        neo4j_config: Dict[str, str] = None
    ):
        self.base_score = base_score
        self.decay_rate = decay_rate
        self.reward_amount = reward_amount
        self.penalty_amount = penalty_amount

        # Use env config if not provided explicitly
        self.neo4j_config = neo4j_config or get_neo4j_config()
        self.neo4j_driver = GraphDatabase.driver(
            self.neo4j_config["url"],
            auth=(self.neo4j_config["username"], self.neo4j_config["password"])
        )

    def score(self, metadata: Dict[str, Any]) -> float:
        """
        Computes the final decayed relevance score for a document.
        """
        score = metadata.get("score", self.base_score)

        last_accessed_at = metadata.get("last_accessed_at")
        logger.debug(f"Scoring: clause_id={metadata.get('clause_id')}, original_score={score}, last_accessed_at={last_accessed_at}, decay_rate={self.decay_rate}")
        if last_accessed_at:
            try:
                dt = datetime.fromisoformat(last_accessed_at)
                age_days = (datetime.now(timezone.utc) - dt).days
                score *= math.exp(-self.decay_rate * age_days)
            except Exception as e:
                logger.debug(f"Error in score decay: {str(e)}")
        logger.debug(f"decayed_score={score}")
        return min(max(score, 0.0), 1.0)

    def reward(self, metadata: Dict[str, Any]) -> None:
        """
        Rewards a document by increasing its score and updating access time.
        """
        score = metadata.get("score", self.base_score)
        score = min(score + self.reward_amount, 1.0)
        metadata["score"] = score
        metadata["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
        logger.debug(f"Document {metadata.get('clause_id')} rewarded. New score: {score}")
        self._persist_metadata(metadata)

    def penalize(self, metadata: Dict[str, Any]) -> None:
        """
        Penalizes a document by decreasing its score.
        """
        score = metadata.get("score", self.base_score)
        score = max(score - self.penalty_amount, 0.0)
        metadata["score"] = score
        logger.debug(f"Document {metadata.get('clause_id')} penalized. New score: {score}")
        self._persist_metadata(metadata)

    def _persist_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Persists updated score and access timestamp back to Neo4j.
        """
        clause_id = metadata.get("clause_id")
        score = metadata.get("score")
        last_accessed_at = metadata.get("last_accessed_at")

        if not clause_id:
            logger.warning("Missing clause_id. Skipping Neo4j update.")
            return

        try:
            with self.neo4j_driver.session() as session:
                session.run(
                    f"""
                    MATCH (n:{self.neo4j_config['node_label']} {{clause_id: $clause_id}})
                    SET n.score = $score,
                        n.last_accessed_at = $last_accessed_at
                    """,
                    clause_id=clause_id,
                    score=score,
                    last_accessed_at=last_accessed_at
                )
            logger.debug(f"Updated clause {clause_id} in Neo4j.")
        except Exception as e:
            logger.error(f"Neo4j update failed: {str(e)}")
