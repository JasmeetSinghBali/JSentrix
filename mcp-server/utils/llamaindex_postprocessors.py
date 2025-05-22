from llama_index.core.schema import NodeWithScore
from llama_index.core.postprocessor.types import BaseNodePostprocessor, NodePostprocessor
from typing import List
from .relevance_scorer import RelevanceScorer
from .logger import get_logger

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

    def __init__(self, scorer: RelevanceScorer):
        self.scorer = scorer

    def postprocess_nodes(self, nodes: list[NodeWithScore], query_str: str = "") -> list[NodeWithScore]:
        for node in nodes:
            custom_score = self.scorer.score(node.metadata)
            logger.debug(f"Node {node.metadata.get('clause_id')} score updated to {custom_score}")
            node.score = custom_score  # Overwrite default similarity score
        return sorted(nodes, key=lambda x: x.score, reverse=True)


class MarkUsedDocsPostprocessor(NodePostprocessor):
    """
    Tags each document node with a 'was_used' flag set to False by default before llm synthesis.
    This gets updated later if the content appears in the final LLM response.
    """

    def __init__(self, relevance_scorer: RelevanceScorer):
        self.relevance_scorer = relevance_scorer

    def postprocess_nodes(
        self, nodes: List[NodeWithScore], query_str: str, **kwargs
    ) -> List[NodeWithScore]:
        for node in nodes:
            node.metadata["was_used"] = False  # Default
        return nodes
