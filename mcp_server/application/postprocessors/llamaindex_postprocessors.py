"""
application/postprocessors/llamaindex_postprocessors.py

Async and sync LlamaIndex node postprocessors for scoring, metadata injection, and hybrid ranking.
"""

from typing import List, Optional, Dict
from pydantic import PrivateAttr
import asyncio

from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.postprocessor.types import BaseNodePostprocessor

from utils.relevance_scorer import RelevanceScorer
from utils.logger import get_logger


logger = get_logger(__name__)


class CustomRelevancePostprocessor(BaseNodePostprocessor):
    """
    Applies RelevanceScorer decay logic to each node and re-ranks results using decayed score. support async execution
    - Reads node.metadata['score'] (original similarity).
    - Applies decay, writes to node.metadata['decayed_score'].
    - Updates node.score to decayed_score for ranking.

    Args:
        scorer (RelevanceScorer): Scorer implementing decay logic
    """

    _scorer: RelevanceScorer = PrivateAttr()

    def __init__(self, scorer: RelevanceScorer):
        super().__init__()
        self._scorer = scorer

    def _process_nodes(self, nodes: List[NodeWithScore]) -> List[NodeWithScore]:
        """
        Shared processing logic for async and sync node processing
        """
        for node in nodes:
            original_score = node.metadata.get("score", node.score)
            decayed_score = self._scorer.score(node.metadata)
            node.metadata["decayed_score"] = decayed_score
            logger.debug(
                f"Node {node.metadata.get('clause_id')} | Original: {original_score:.3f} → Decayed: {decayed_score:.3f}"
            )
            # 📌 LlamaIndex expects the score attribute of NodeWithScore to represent the current ranking metric (e.g., similarity, rerank, or your custom decay/hybrid score
            node.score = decayed_score  # Overwrite default similarity score
            logger.debug(
                f"Node {node.metadata.get('clause_id')} | Original: {original_score:.3f} → Decayed: {decayed_score:.3f}"
            )
            # The LlamaIndex response synthesis and subsequent pipeline steps will use the updated .score for sorting, filtering, or context selection.
        return sorted(nodes, key=lambda x: x.score, reverse=True)

    def _postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Sync: Apply score decay and re-rank nodes."""
        # Use query_bundle if needed for scoring logic
        query_str = query_bundle.query_str if query_bundle else ""
        logger.debug(f"Applying decay to nodes for query: {query_str}")
        return self._process_nodes(nodes)

    async def _aprocess_nodes(self, nodes: List[NodeWithScore]) -> List[NodeWithScore]:
        """Full async processing when supported by scorer, with eror handl logs per node"""
        processed = []
        for node in nodes:
            try:
                metadata = node.metadata.copy()

                # Async score calculation
                if hasattr(self._scorer, "ascore"):
                    metadata["decayed_score"] = await self._scorer.ascore(metadata)
                else:
                    metadata["decayed_score"] = self._scorer.score(metadata)

                node.score = metadata["decayed_score"]
                node.metadata = metadata
                processed.append(node)
            except Exception as e:
                logger.error(
                    f"Error processing node {node.metadata.get('clause_id',None)}: {e}"
                )
        return sorted(processed, key=lambda x: x.score, reverse=True)

    async def _apostprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Async: Apply score decay and rerank nodes."""
        query_str = query_bundle.query_str if query_bundle else ""
        logger.debug(f"[Async] Applying decay to node for query: {query_str}")

        # If scorer has async capabilities, use them
        if hasattr(self._scorer, "ascore"):
            return await self._aprocess_nodes(nodes)
        # Fallback to threadpool for sync scoring with err handl
        try:
            return await asyncio.to_thread(self._process_nodes, nodes)
        except Exception as e:
            logger.error(f"Error in threadpool scoring: {e}")
            return []


class MarkUsedDocsPostprocessor(BaseNodePostprocessor):
    """
    Tags each document node with a 'was_used' flag set to False by default before llm synthesis.
    This gets updated later if the content appears in the final LLM response.
    Async compatible
    """

    _scorer: RelevanceScorer = PrivateAttr()

    def __init__(self, scorer: RelevanceScorer):
        super().__init__()
        self._scorer = scorer

    def _process_nodes(self, nodes: List[NodeWithScore]) -> List[NodeWithScore]:
        """Shared processing tag nodes with inital usage flag as False"""
        for node in nodes:
            node.metadata["was_used"] = False  # default
        return nodes

    def _postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Sync: Tag nodes with initial usage flag"""
        return self._process_nodes(nodes)

    async def _apostprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Async: Tag nodes with initial usage flag"""
        try:
            return await asyncio.to_thread(self._process_nodes, nodes)
        except Exception as e:
            logger.error(f"Error tagging nodes with usage flag: {e}")
            return []


class MetadataInjectionPostprocessor(BaseNodePostprocessor):
    """
    Injects dynamic metadata (eg from langchain) into llamaindex nodes by clause_id
    supports async safe with thread-safe logging
    """

    _dynamic_metadata: Dict[str, dict] = PrivateAttr()

    def __init__(self, dynamic_metadata: Dict[str, Dict]):
        super().__init__()
        self._dynamic_metadata = dynamic_metadata

    def _process_nodes(self, nodes: List[NodeWithScore]) -> List[NodeWithScore]:
        """Shared metadata injection logic"""
        for node in nodes:
            logger.debug(
                "Raw node metadata from Neo4j (in postprocessor):", node.metadata
            )
            logger.debug("Before injection:", node.metadata)
            clause_id = node.metadata.get("clause_id")
            if clause_id and clause_id in self._dynamic_metadata:
                node.metadata.update(self._dynamic_metadata[clause_id])
                logger.debug("After injection:", node.metadata)
                logger.debug(
                    f"Injected metadata for clause_id {clause_id}: {self._dynamic_metadata[clause_id]}"
                )
        return nodes

    def _postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Sync: Inject metadata into nodes."""
        return self._process_nodes(nodes)

    async def _apostprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Async: Inject metadata into nodes."""
        try:
            return await asyncio.to_thread(self._process_nodes, nodes)
        except Exception as e:
            logger.error(f"Error injecting metadata into nodes: {e}")
            return []


class HybridScorePostprocessor(BaseNodePostprocessor):
    """
    Overwrites node.score with hybrid_score from metadata (if present) as llama refers to the 'score' by default

    Returns
        list of nodes with score sorted in highest to lowest order
    """

    def _process_nodes(self, nodes: List[NodeWithScore]) -> List[NodeWithScore]:
        """Shared hybrid scoring applied logic"""
        for node in nodes:
            if "hybrid_score" in node.metadata:
                node.score = node.metadata["hybrid_score"]
        return sorted(nodes, key=lambda x: x.score, reverse=True)

    def _postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        return self._process_nodes(nodes)

    async def _apostprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        try:
            return await asyncio.to_thread(self._process_nodes, nodes)
        except Exception as e:
            logger.error(f"Error applying hybrid score: {e}")
            return []
