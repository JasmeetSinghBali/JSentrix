from llama_index.core.schema import NodeWithScore
from llama_index.core.query_engine import BaseQueryEngine
from typing import Any, Dict
from difflib import SequenceMatcher
from .relevance_scorer import RelevanceScorer
from .logger import get_logger

logger = get_logger(__name__)

class RewardingQueryEngineWrapper(BaseQueryEngine):
    """
    Wraps a QueryEngine and applies reward/penalty after response generation
    based on whether each node was used in the final answer.
    """

    def __init__(self, query_engine: BaseQueryEngine, scorer: RelevanceScorer, similarity_threshold: float = 0.85):
        self._query_engine = query_engine
        self._scorer = scorer
        self._similarity_threshold = similarity_threshold

    def _is_node_used(self, node_text: str, response_text: str) -> bool:
        ratio = SequenceMatcher(None, node_text.lower(), response_text.lower()).ratio()
        return ratio >= self._similarity_threshold

    def query(self, query_str: str, **kwargs: Any) -> Any:
        logger.debug("Running wrapped query engine with post-reward/penalty logic")
        response = self._query_engine.query(query_str, **kwargs)
        
        # If the underlying engine returns a structured response with source_nodes
        source_nodes: list[NodeWithScore] = getattr(response, "source_nodes", [])
        response_text: str = str(getattr(response, "response", ""))

        for node in source_nodes:
            metadata = node.metadata
            node_text = node.node.get_content()

            if self._is_node_used(node_text, response_text):
                self._scorer.reward(metadata)
            else:
                self._scorer.penalize(metadata)

        return response
