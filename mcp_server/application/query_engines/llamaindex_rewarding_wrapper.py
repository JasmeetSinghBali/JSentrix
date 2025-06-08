"""
application/query_engines/llamaindex_rewarding_wrapper.py

Async and sync wrapper for a LlamaIndex QueryEngine that rewards/penalizes source nodes
based on their usage in the final response.
"""

from typing import Any, List
from difflib import SequenceMatcher

from llama_index.core.schema import NodeWithScore
from llama_index.core.query_engine import BaseQueryEngine
from llama_index.core import Response

from utils.relevance_scorer import RelevanceScorer
from utils.logger import get_logger
from utils.retry import retry, async_retry

logger = get_logger(__name__)


class RewardingQueryEngineWrapper(BaseQueryEngine):
    """
    Wraps a QueryEngine to reward/penalize nodes based on their contribution to the response.

    Support both sync and async query flows, with retry logic

    Args:
        query_engine: Underlying query engine to wrap.
        scorer: Relevance scorer for reward/penalty logic.
        similarity_threshold: Text similarity threshold (0-1) to consider a node "used".
    """

    def __init__(
        self,
        query_engine: BaseQueryEngine,
        scorer: RelevanceScorer,
        similarity_threshold: float = 0.85,
    ):
        # preserve callback manager from wrapped engine
        callback_manager = getattr(query_engine, "callback_manager", None)
        super().__init__(callback_manager=callback_manager)
        self._query_engine = query_engine
        self._scorer = scorer
        self._similarity_threshold = similarity_threshold

    def _is_node_used(self, node_text: str, response_text: str) -> bool:
        """
        Checks if node text is sufficiently similar to response text.

        Args:
            node_text (str): Text from the source node.
            response_text (str): Final response text.

        Returns:
            bool: True if node is considered "used" in the response.
        """
        ratio = SequenceMatcher(None, node_text.lower(), response_text.lower()).ratio()
        return ratio >= self._similarity_threshold

    def _reward_nodes(
        self, source_nodes: List[NodeWithScore], response_text: str
    ) -> None:
        """
        Applies reward/penalty to nodes based on usage in response.
        Args:
            source_nodes (List[NodeWithScore]): Nodes to evaluate
            response_text (str): The generated text
        """
        for node in source_nodes:
            node_text = node.node.get_content()
            if self._is_node_used(node_text, response_text):
                self._scorer.reward(node.metadata)
                logger.debug(f"Rewarded node: {node.metadata}")
            else:
                self._scorer.penalize(node.metadata)
                logger.debug(f"Penalized node: {node.metadata}")

    def _query(self, query_str: str, **kwargs: Any) -> Response:
        """
        Sync query with post-processing rewards.

        Args:
            query_str(str): The input query string

        Returns:
            Response: The qury engine response
        """
        logger.debug(
            "Running wrapped query engine(sync) with post-reward/penalty logic"
        )
        response = self._query_engine.query(query_str, **kwargs)
        # response.response holds response text
        self._reward_nodes(response.source_nodes, str(response.response))
        return response

    async def _aquery(self, query_str: str, **kwargs: Any) -> Response:
        """
        Asynchronous query with post-processing rewards.

        Args:
            query_str (str): The input query string.

        Returns:
            Response: The query engine response.
        """
        logger.debug(
            "Running wrapped query engine(async) with post-reward/penalty logic"
        )
        response = await self._query_engine.aquery(query_str, **kwargs)
        self._reward_nodes(response.source_nodes, str(response.response))
        return response

    def _get_prompt_modules(self) -> Any:
        """Delegate to underlying engine if available."""
        if hasattr(self._query_engine, "_get_prompt_modules"):
            return self._query_engine._get_prompt_modules()
        return None

    # 📌 Exposing the internal _query and _aquery methods as public query and aquery methods, with retry logic applied to query
    @retry(max_retries=3, delay=1.0, exceptions=(TimeoutError,), logger=logger.info)
    def query(self, query_str: str, **kwargs: Any) -> Response:
        """Public sync query with retry logic."""
        return self._query(query_str, **kwargs)

    @async_retry(
        max_retries=3, delay=1.0, exceptions=(TimeoutError,), logger=logger.info
    )
    async def aquery(self, query_str: str, **kwargs: Any) -> Response:
        """Public async query with retry logic."""
        return await self._aquery(query_str, **kwargs)
