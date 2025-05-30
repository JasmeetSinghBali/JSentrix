"""
utils/embedding_utils.py

Centralized embedding utility for consistent model/config across the system.
"""

from langchain_huggingface import HuggingFaceEmbeddings
from llama_index.embeddings.huggingface import (
    HuggingFaceEmbedding as LlamaHuggingFaceEmbedding,
)
from utils.logger import get_logger

logger = get_logger("jsentrix")


def get_langchain_embedding_model():
    """
    Returns a HuggingFaceEmbeddings instance for LangChain.
    """
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_llamaindex_embedding_model():
    """
    Returns a HuggingFaceEmbedding instance for LlamaIndex.
    """
    return LlamaHuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device="cpu",
        normalize=True,
    )
