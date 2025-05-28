"""
application/postprocessors/llamaindex_postprocessors.py

Custom LlamaIndex node postprocessors for advanced scoring and metadata injection.
"""
from typing import List, Optional, Dict
from pydantic import PrivateAttr

from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.postprocessor.types import BaseNodePostprocessor

from utils.relevance_scorer import RelevanceScorer
from utils.logger import get_logger


logger = get_logger(__name__)

class CustomRelevancePostprocessor(BaseNodePostprocessor):
    """
    Applies RelevanceScorer decay logic to each node and re-ranks results using decayed score.
    - Reads node.metadata['score'] (original similarity).
    - Applies decay, writes to node.metadata['decayed_score'].
    - Updates node.score to decayed_score for ranking.
    """
    _scorer: RelevanceScorer = PrivateAttr()

    def __init__(self, scorer: RelevanceScorer):
        super().__init__()
        self._scorer = scorer

    def _postprocess_nodes(
            self, 
            nodes: List[NodeWithScore], 
            query_bundle: Optional[QueryBundle]=None
    ) -> List[NodeWithScore]:
        # Use query_bundle if needed for scoring logic
        query_str = query_bundle.query_str if query_bundle else ""
        logger.debug(f"Applying decay to nodes for query: {query_str}")
        for node in nodes:
            original_score = node.metadata.get('score', node.score)
            decayed_score = self._scorer.score(node.metadata)
            node.metadata['decayed_score'] = decayed_score
            logger.debug(f"Node {node.metadata.get('clause_id')} | Original: {original_score:.3f} → Decayed: {decayed_score:.3f}")
            # 📌 LlamaIndex expects the score attribute of NodeWithScore to represent the current ranking metric (e.g., similarity, rerank, or your custom decay/hybrid score
            node.score = decayed_score  # Overwrite default similarity score
            # The LlamaIndex response synthesis and subsequent pipeline steps will use the updated .score for sorting, filtering, or context selection.
        return sorted(nodes, key=lambda x: x.score, reverse=True)


class MarkUsedDocsPostprocessor(BaseNodePostprocessor):
    """
    Tags each document node with a 'was_used' flag set to False by default before llm synthesis.
    This gets updated later if the content appears in the final LLM response.
    """
    _scorer: RelevanceScorer = PrivateAttr()

    def __init__(self, scorer: RelevanceScorer):
        super().__init__()
        self._scorer = scorer

    def _postprocess_nodes(
        self, 
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        for node in nodes:
            node.metadata["was_used"] = False  # Default
        return nodes


class MetadataInjectionPostprocessor(BaseNodePostprocessor):
    """
    Injects dynamic metadata (eg from langchain) into llamaindex nodes by clause_id
    """
    _dynamic_metadata: Dict[str,dict]=PrivateAttr()

    def __init__(self,dynamic_metadata: Dict[str,Dict]):
        super().__init__()
        self._dynamic_metadata=dynamic_metadata
    
    def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle]=None
    ) -> List[NodeWithScore]:
        for node in nodes:
            logger.debug("Raw node metadata from Neo4j (in postprocessor):", node.metadata)
            logger.debug("Before injection:", node.metadata)
            clause_id=node.metadata.get("clause_id")
            if clause_id and clause_id in self._dynamic_metadata:
                node.metadata.update(self._dynamic_metadata[clause_id])
                logger.debug("After injection:", node.metadata)
                logger.debug(f"Injected metadata for clause_id {clause_id}: {self._dynamic_metadata[clause_id]}")
        return nodes

class HybridScorePostprocessor(BaseNodePostprocessor):
    """
    Overwrites node.score with hybrid_score from metadata (if present) as llama refers to the 'score' by default

    Returns
        list of nodes with score sorted in highest to lowest order
    """
    def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle]=None
    )->List[NodeWithScore]:
        for node in nodes:
            if "hybrid_score" in node.metadata:
                node.score=node.metadata["hybrid_score"]
        return sorted(nodes, key=lambda x: x.score, reverse=True)