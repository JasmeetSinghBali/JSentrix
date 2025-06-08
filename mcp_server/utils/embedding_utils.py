"""
utils/embedding_utils.py

Centralized embedding utility for consistent model/config across the system.
Supports singleton pattern to avoid loading the same model multiple times.

Usage:
    from utils.embedding_utils import get_langchain_embedding_model

    embedder = get_langchain_embedding_model(device="cpu")
    embeddings = embedder.embed_documents(["hello world"])
"""

from langchain_huggingface import HuggingFaceEmbeddings
from llama_index.embeddings.huggingface import (
    HuggingFaceEmbedding as LlamaHuggingFaceEmbedding,
)
from utils.logger import get_logger
from typing import Optional
import threading

logger = get_logger("jsentrix")

# Singleton pattern to avoid repeated model loading
_langchain_embedding_model: Optional[HuggingFaceEmbeddings] = None
_llamaindex_embedding_model: Optional[LlamaHuggingFaceEmbedding] = None
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
