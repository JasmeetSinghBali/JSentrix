"""
utils/summarizer.py

Lightweight summarizer using T5-small for CPU-only environments.
Handles long texts via chunking and recursive summarization.
"""

from transformers import pipeline
from typing import Optional, List
from utils.logger import get_logger

logger = get_logger("jsentrix")


class T5Summarizer:
    """
    Lightweight summarizer using T5-small for CPU-only environments.
    Handles long texts via chunking and recursive summarization.
    """

    def __init__(
        self,
        model_name: str = "t5-small",
        max_input_length: int = 512,
        max_summary_length: int = 150,
        min_summary_length: int = 30,
        device: int = -1,  # -1 = CPU
    ):
        """
        Initializes the summarization pipeline.
        """
        self.summarizer = pipeline(
            "summarization",
            model=model_name,
            tokenizer=model_name,
            device=device,  # -1 for CPU
        )
        self.max_input_length = max_input_length
        self.max_summary_length = max_summary_length
        self.min_summary_length = min_summary_length

    def summarize(self, text: str) -> Optional[str]:
        """
        Summarizes the given text. Handles long texts via chunking and recursion.
        """
        try:
            if not text or not text.strip():
                return None
            # Handle long texts by chunking if needed
            if len(text) > self.max_input_length:
                return self._summarize_long_text(text)
            result = self.summarizer(
                text,
                max_length=self.max_summary_length,
                min_length=self.min_summary_length,
                do_sample=False,
            )
            return result[0]["summary_text"]
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            return None

    def _summarize_long_text(self, text: str) -> str:
        """
        Handles texts longer than max_input_length via chunking and recursive summarization.
        """
        chunks = [
            text[i : i + self.max_input_length]
            for i in range(0, len(text), self.max_input_length)
        ]
        summaries: List[str] = []
        for chunk in chunks:
            summary = self.summarize(chunk)
            if summary:
                summaries.append(summary)
        combined = " ".join(summaries)
        if len(combined) > self.max_input_length:
            return self.summarize(combined)  # Recursive summarization
        return combined
