from llama_index.core import VectorStoreIndex
from llama_index.llms.ollama import Ollama
from utils.relevance_scorer import RelevanceScorer
from utils.llamaindex_postprocessors import (
    CustomRelevancePostprocessor,
    MetadataInjectionPostprocessor,
    HybridScorePostprocessor
)
from utils.llamaindex_rewarding_wrapper import RewardingQueryEngineWrapper
from utils.logger import get_logger
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.settings import Settings

logger = get_logger(__name__)

def get_llamaindex_query_engine_from_docs(
    docs,
    dynamic_metadata_by_clause_id=None,
    llm=None
):
    """
    Returns a LlamaIndex query engine built from provided docs,
    with custom postprocessors and reward logic.
    """
    # 1. Set up your custom embedding and LLM (use passed llm if provided)
    embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    if llm is None:
        llm = Ollama(
            model="qwen3:1.7b", 
            request_timeout=180.0)  # 3 minutes, adjust as needed

    # 2. Set global defaults for LlamaIndex modules
    Settings.embed_model = embed_model
    Settings.llm = llm

    # 3. Build scorer and postprocessors
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
        postprocessors.append(MetadataInjectionPostprocessor(dynamic_metadata_by_clause_id))
        postprocessors.append(CustomRelevancePostprocessor(scorer))
        postprocessors.append(HybridScorePostprocessor())
    else:
        postprocessors.append(CustomRelevancePostprocessor(scorer)) # decay always get applied

    # 4. Build index from docs, passing the explicit embedding model
    index = VectorStoreIndex.from_documents(docs, embed_model=embed_model)

    # 5. Build query engine with postprocessors and LLM
    query_engine = index.as_query_engine(
        llm=llm,
        node_postprocessors=postprocessors
    )

    # 6. Wrap for reward/penalty logic
    query_engine = RewardingQueryEngineWrapper(query_engine, scorer)

    return query_engine
