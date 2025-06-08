"""
utils/summarizer.py

Lightweight summarizer using T5-small for CPU-only environments.
Handles long texts via chunking and recursive summarization.
Supports both synchronous and asynchronous summarization for scalable pipelines.

Usage:
    #sync
    summarizer = T5Summarizer()
    summary = summarizer.summarize(long_text)

    #async
    summarizer = T5Summarizer()
    summary = await summarizer.async_summarize(long_text)
    # or for very long text:
    summary = await summarizer.async_summarize_long_text(long_text)


"""

from transformers import pipeline
from typing import Optional, List
from utils.logger import get_logger
import asyncio

logger = get_logger("jsentrix")


class T5Summarizer:
    """
    Lightweight summarizer using T5-small for CPU-only environments.
    Handles long texts via chunking and recursive summarization.
    Supports both sync and async summarization.
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
        Synchronously summarizes the given text.
        Handles long texts via chunking and recursion.
        """
        try:
            if not text or not text.strip():
                return None
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

    async def async_summarize(self, text: str) -> Optional[str]:
        """
        Asynchronously summarizes the given text.
        Runs the sync summarization in a thread pool to avoid blocking the event loop.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.summarize, text)

    async def async_summarize_long_text(self, text: str) -> Optional[str]:
        """
        Asynchronously handles long texts via chunking and recursive summarization.
        Runs chunk summarization in a thread pool for each chunk.
        """
        if not text or not text.strip():
            return None
        if len(text) <= self.max_input_length:
            return await self.async_summarize(text)

        chunks = [
            text[i : i + self.max_input_length]
            for i in range(0, len(text), self.max_input_length)
        ]
        # Run chunk summarization concurrently
        summaries = await asyncio.gather(
            *(self.async_summarize(chunk) for chunk in chunks)
        )
        combined = " ".join(filter(None, summaries))
        if len(combined) > self.max_input_length:
            return await self.async_summarize(combined)  # Recursive
        return combined
