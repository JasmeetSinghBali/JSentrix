"""
application/retrievers/llamaindex_retriever.py

Builds a LlamaIndex query engine with custom postprocessors and reward logic.
Supports both synchronous and asynchronous summarization for scalable pipelines.
"""

from typing import List, Optional, Dict, Any

from llama_index.core import VectorStoreIndex
from llama_index.llms.ollama import Ollama
from llama_index.core.settings import Settings


from application.postprocessors.llamaindex_postprocessors import (
    CustomRelevancePostprocessor,
    MetadataInjectionPostprocessor,
    HybridScorePostprocessor,
)
from application.query_engines.llamaindex_rewarding_wrapper import (
    RewardingQueryEngineWrapper,
)

from utils.embedding_utils import get_llamaindex_embedding_model
from utils.logger import get_logger
from utils.relevance_scorer import RelevanceScorer
from utils.summarizer import T5Summarizer

import asyncio

logger = get_logger("jsentrix")


def get_llamaindex_query_engine_from_docs(
    docs: List[Any],
    dynamic_metadata_by_clause_id: Optional[Dict[str, Dict]] = None,
    llm: Optional[Any] = None,
    embed_model: Optional[Any] = None,
    summarizer: Optional[T5Summarizer] = None,
) -> Any:
    """
    Returns a LlamaIndex query engine built from provided docs,
    with custom postprocessors and reward logic.

    Args:
        docs: List of LlamaIndex Document objects.
        dynamic_metadata_by_clause_id: Optional dict for metadata injection.
        llm: Optional LLM instance (defaults to Ollama qwen3:1.7b).
        embed_model: Optional embedding model (defaults to MiniLM-L6-v2).
        summarizer: Optional summarizer (defaults to T5Summarizer).

    Returns:
        A LlamaIndex query engine wrapped with reward/penalty logic.
    """
    # 1. Set up your custom embedding and LLM (use passed llm if provided)
    embed_model = embed_model or get_llamaindex_embedding_model()
    if llm is None:
        llm = Ollama(
            model="qwen3:1.7b", request_timeout=180.0
        )  # 3 minutes, adjust as needed

    # 2. Set global defaults for LlamaIndex modules
    Settings.embed_model = embed_model
    Settings.llm = llm

    # 3. enrich docs with summaries
    summarizer = summarizer or T5Summarizer()
    for doc in docs:
        # LlamaIndex docs typically have .text or .get_content()
        text = getattr(doc, "text", None) or getattr(doc, "get_content", lambda: None)()
        if text and ("summary" not in doc.metadata or not doc.metadata["summary"]):
            summary = summarizer.summarize(text)
            doc.metadata["summary"] = summary
            logger.debug(f"Summary added to doc: {summary}")

    # 4. Build scorer and postprocessors
    scorer = RelevanceScorer()
    postprocessors = []
    # Postprocessor Order
    # MetadataInjectionPostprocessor should come first (injects external scores/metadata).
    # CustomRelevancePostprocessor should come after (applies decay to the injected or original scores).
    # HybridScorePostprocessor (if you want to use a hybrid score for reranking) should come after CustomRelevancePostprocessor and should set node.score from hybrid_score in metadata.
    # If you use both, the typical order is:
    # MetadataInjectionPostprocessor
    # CustomRelevancePostprocessor
    # HybridScorePostprocessor
    if dynamic_metadata_by_clause_id:
        postprocessors.append(
            MetadataInjectionPostprocessor(dynamic_metadata_by_clause_id)
        )
        postprocessors.append(CustomRelevancePostprocessor(scorer))
        postprocessors.append(HybridScorePostprocessor())
    else:
        postprocessors.append(
            CustomRelevancePostprocessor(scorer)
        )  # decay always get applied

    # 5. Build index from docs, passing the explicit embedding model
    index = VectorStoreIndex.from_documents(docs, embed_model=embed_model)

    # 6. Build query engine with postprocessors and LLM
    query_engine = index.as_query_engine(llm=llm, node_postprocessors=postprocessors)

    # 7. Wrap for reward/penalty logic
    query_engine = RewardingQueryEngineWrapper(query_engine, scorer)

    return query_engine


async def async_get_llamaindex_query_engine_from_docs(
    docs: List[Any],
    dynamic_metadata_by_clause_id: Optional[Dict[str, Dict]] = None,
    llm: Optional[Any] = None,
    embed_model: Optional[Any] = None,
    summarizer: Optional[T5Summarizer] = None,
) -> Any:
    """
    Async version: Returns a LlamaIndex query engine built from provided docs,
    with custom postprocessors and reward logic.
    Summarization is performed asynchronously for each doc.

    Args:
        docs: List of LlamaIndex Document objects.
        dynamic_metadata_by_clause_id: Optional dict for metadata injection.
        llm: Optional LLM instance (defaults to Ollama qwen3:1.7b).
        embed_model: Optional embedding model (defaults to MiniLM-L6-v2).
        summarizer: Optional summarizer (defaults to T5Summarizer).

    Returns:
        A LlamaIndex query engine wrapped with reward/penalty logic.
    """
    embed_model = embed_model or get_llamaindex_embedding_model()
    if llm is None:
        llm = Ollama(model="qwen3:1.7b", request_timeout=180.0)

    Settings.embed_model = embed_model
    Settings.llm = llm

    summarizer = summarizer or T5Summarizer()

    semaphore = asyncio.Semaphore(8)  # Limit to 8 concurrent summaries

    async def summarize_doc(doc):
        try:
            async with semaphore:
                text = (
                    getattr(doc, "text", None)
                    or getattr(doc, "get_content", lambda: None)()
                )
                if text and (
                    "summary" not in doc.metadata or not doc.metadata["summary"]
                ):
                    summary = await summarizer.async_summarize(text)
                    doc.metadata["summary"] = summary
                    logger.debug(f"Summary added to doc: {summary}")
        except Exception as e:
            logger.error(f"Failed to summarize doc {getattr(doc, 'id', None)}: {e}")

    await asyncio.gather(*(summarize_doc(doc) for doc in docs))

    scorer = RelevanceScorer()
    postprocessors = []
    if dynamic_metadata_by_clause_id:
        postprocessors.append(
            MetadataInjectionPostprocessor(dynamic_metadata_by_clause_id)
        )
        postprocessors.append(CustomRelevancePostprocessor(scorer))
        postprocessors.append(HybridScorePostprocessor())
    else:
        postprocessors.append(CustomRelevancePostprocessor(scorer))

    index = VectorStoreIndex.from_documents(docs, embed_model=embed_model)
    query_engine = index.as_query_engine(llm=llm, node_postprocessors=postprocessors)
    query_engine = RewardingQueryEngineWrapper(query_engine, scorer)
    return query_engine
