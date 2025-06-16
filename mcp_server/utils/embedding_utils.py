"""
utils/embedding_utils.py

Centralized embedding utility for consistent model/config across the system.
Supports singleton pattern to avoid loading the same model multiple times.
Provides async batch embedding for high-throughput workflows.

Usage:
    from utils.embedding_utils import (
        get_langchain_embedding_model,
        get_llamaindex_embedding_model,
        async_batch_embed_documents,
    )

    # Sync usage (legacy)
    embedder = get_langchain_embedding_model()
    embeddings = embedder.embed_documents(["hello world"])

    # Async batch embedding (recommended for async flows)
    embeddings = await async_batch_embed_documents(
        ["doc1", "doc2", ...],
        backend="fastembed",  # or "langchain" or "llamaindex"
        device="cpu"
    )
"""

from langchain_huggingface import HuggingFaceEmbeddings
from llama_index.embeddings.huggingface import (
    HuggingFaceEmbedding as LlamaHuggingFaceEmbedding,
)
from utils.logger import get_logger
from typing import Optional, List, Union
import threading
import asyncio

try:
    from qdrant_client.fastembed import TextEmbedding as FastEmbedTextEmbedding

    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False

logger = get_logger("embedding_utils")

# Singleton pattern to avoid repeated model loading
_langchain_embedding_model: Optional[HuggingFaceEmbeddings] = None
_llamaindex_embedding_model: Optional[LlamaHuggingFaceEmbedding] = None
_fastembed_model: Optional["FastEmbedTextEmbedding"] = None
_model_lock = threading.Lock()


def get_langchain_embedding_model(device: str = "cpu") -> HuggingFaceEmbeddings:
    """
    Returns a singleton HuggingFaceEmbeddings instance for LangChain.

    Args:
        device (str): Device to load the model on, e.g., "cpu" or "cuda".

    Returns:
        HuggingFaceEmbeddings: Embedding model instance.
    """
    global _langchain_embedding_model
    if _langchain_embedding_model is None:
        with _model_lock:
            if _langchain_embedding_model is None:
                logger.info(f"Loading LangChain HuggingFaceEmbeddings on {device}...")
                _langchain_embedding_model = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs={"device": device},
                    encode_kwargs={"normalize_embeddings": True},
                )
    return _langchain_embedding_model


def get_llamaindex_embedding_model(device: str = "cpu") -> LlamaHuggingFaceEmbedding:
    """
    Returns a singleton HuggingFaceEmbedding instance for LlamaIndex.

    Args:
        device (str): Device to load the model on, e.g., "cpu" or "cuda".

    Returns:
        LlamaHuggingFaceEmbedding: Embedding model instance.
    """
    global _llamaindex_embedding_model
    if _llamaindex_embedding_model is None:
        with _model_lock:
            if _llamaindex_embedding_model is None:
                logger.info(f"Loading LlamaIndex HuggingFaceEmbedding on {device}...")
                _llamaindex_embedding_model = LlamaHuggingFaceEmbedding(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    device=device,
                    normalize=True,
                )
    return _llamaindex_embedding_model


def get_fastembed_model(
    model_name: str = "BAAI/bge-small-en-v1.5",
) -> Optional["FastEmbedTextEmbedding"]:
    """
    Returns a singleton FastEmbedTextEmbedding instance if fastembed is available.

    Args:
        model_name (str): Name of the fastembed model.

    Returns:
        FastEmbedTextEmbedding or None
    """
    global _fastembed_model
    if not FASTEMBED_AVAILABLE:
        logger.warning(
            "FastEmbed is not installed. Run: pip install 'qdrant-client[fastembed]'"
        )
        return None
    if _fastembed_model is None:
        with _model_lock:
            if _fastembed_model is None:
                logger.info(f"Loading FastEmbedTextEmbedding model: {model_name}")
                _fastembed_model = FastEmbedTextEmbedding(model_name=model_name)
    return _fastembed_model


async def async_batch_embed_documents(
    documents: List[str],
    backend: str = "langchain",
    device: str = "cpu",
    batch_size: int = 32,
    model_name: Optional[str] = None,
) -> List[List[float]]:
    """
    Async batch embed documents using the specified backend.

    Args:
        documents (List[str]): List of documents to embed.
        backend (str): "langchain", "llamaindex", or "fastembed".
        device (str): Device for model ("cpu" or "cuda").
        batch_size (int): Batch size for embedding.
        model_name (Optional[str]): For FastEmbed, override model name.

    Returns:
        List[List[float]]: List of embedding vectors.
    """
    if backend == "langchain":
        embedder = get_langchain_embedding_model(device=device)
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, embedder.embed_documents, documents)
    elif backend == "llamaindex":
        embedder = get_llamaindex_embedding_model(device=device)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, embedder.get_text_embedding_batch, documents
        )
    elif backend == "fastembed":
        if not FASTEMBED_AVAILABLE:
            raise ImportError(
                "FastEmbed is not installed. Run: pip install 'qdrant-client[fastembed]'"
            )
        embedder = get_fastembed_model(
            model_name=model_name or "BAAI/bge-small-en-v1.5"
        )
        # FastEmbed is natively fast, but not async, so use thread pool
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: list(embedder.embed(documents)))
    else:
        raise ValueError(f"Unknown embedding backend: {backend}")
