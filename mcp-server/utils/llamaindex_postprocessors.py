from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from typing import List,Optional,Any
from .relevance_scorer import RelevanceScorer
from .logger import get_logger
from pydantic import PrivateAttr

logger = get_logger(__name__)

class CustomRelevancePostprocessor(BaseNodePostprocessor):
    """
    Applies RelevanceScorer decay logic to each node and re-ranks results using decayed score.
    NodeWithScore is the internal LlamaIndex class used to hold results and scores.
    This postprocessor:

    - Reads node.metadata (from Neo4j custom query).
    - Applies RelevanceScorer.
    - Replaces the .score with custom_score.
    - Sorts accordingly.
    """
    _scorer: RelevanceScorer = PrivateAttr()

    def __init__(self, scorer: RelevanceScorer):
        print("INIT CALLED", scorer)
        super().__init__()
        self._scorer = scorer

    def _postprocess_nodes(self, nodes: list[NodeWithScore], query_bundle: Optional[QueryBundle]=None) -> list[NodeWithScore]:
        print("SCORER IS", self._scorer)
        # Use query_bundle if needed for scoring logic
        query_str = query_bundle.query_str if query_bundle else ""
        logger.debug(f"Applying decay to nodes for query: {query_str}")
        for node in nodes:
            custom_score = self._scorer.score(node.metadata)
            logger.debug(f"Node {node.metadata.get('clause_id')} | "
                        f"Original: {node.score:.3f} → Decayed: {custom_score:.3f}")
            # 📌 LlamaIndex expects the score attribute of NodeWithScore to represent the current ranking metric (e.g., similarity, rerank, or your custom decay/hybrid score
            node.score = custom_score  # Overwrite default similarity score
            # The LlamaIndex response synthesis and subsequent pipeline steps will use the updated .score for sorting, filtering, or context selection.
        return sorted(nodes, key=lambda x: x.score, reverse=True)


class MarkUsedDocsPostprocessor(BaseNodePostprocessor):
    """
    Tags each document node with a 'was_used' flag set to False by default before llm synthesis.
    This gets updated later if the content appears in the final LLM response.
    """
    _scorer: RelevanceScorer = PrivateAttr()

    def __init__(self, scorer: RelevanceScorer):
        print("INIT CALLED", scorer)
        super().__init__()
        self._scorer = scorer

    def _postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        for node in nodes:
            node.metadata["was_used"] = False  # Default
        return nodes
