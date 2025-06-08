"""
domain/models.py

Domain models for clauses and their metadata.
These models are used throughout the ingestion pipeline and downstream
systems for type safety, validation, and clear data contracts.

Usage:
    from domain.models import Clause, ClauseMetaData
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class ClauseMetaData(BaseModel):
    """
    Metadata for a compliance clause, including enrichment fields.
    """

    category: Optional[str] = Field(
        default=None,
        description="High-level category of the clause (eg. AML, KYC, Sanctions)",
    )
    section_header: Optional[str] = Field(
        default=None, description="Section of header in the source document"
    )
    references: List[str] = Field(
        default_factory=list, description="List of legal or document references"
    )
    amends: List[str] = Field(
        default_factory=list, description="List of clauses this one amends"
    )
    overrides: List[str] = Field(
        default_factory=list, description="List of clauses this one overrides"
    )
    source: Optional[str] = Field(
        default=None, description="Source document or system for this clause"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Short summary of the clause (added during enrichment)",
    )
    num_sentences: Optional[int] = Field(
        default=None, description="Number of sentences in the clause"
    )
    entities: Optional[List[str]] = Field(
        default=None, description="Named entities extracted from the clause"
    )
    clause_type: Optional[str] = Field(
        default=None, description="Type of clause, e.g., obligation, prohibition, etc."
    )
    clause_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for the clause (for graph relationships)",
    )
    title: Optional[str] = Field(
        default=None,
        description="Clause title or heading (can be duplicated for convenience)",
    )


# ... pydantic required field
class Clause(BaseModel):
    """
    Represents a compliance clause with its core text and metadata.
    """

    id: str = Field(..., description="Unique identifier for the clause")
    title: Optional[str] = Field(default=None, description="Clause title or heading")
    text: str = Field(..., description="Full text of the clause")
    metadata: ClauseMetaData = Field(
        ..., description="Associated metadata for the clause"
    )


class MemoryEvent(BaseModel):
    """
    Usage:
        event = MemoryEvent(
            user_id="alice",
            agent_name="LlamaIndexAgent",
            prompt="What is AML?",
            llm_response="AML stands for Anti-Money Laundering...",
            relevant_clause_ids=["C1", "C2"],
            scores={"similarity": 0.92},
            extra_context={"source": "neo4j"}
        )
        print(event.json(indent=2))
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique event ID"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Event timestamp (ISO)",
    )
    user_id: Optional[str] = Field(default=None, description="User or session ID")
    agent_name: str = Field(..., description="Name of the agent")
    prompt: str = Field(..., description="Prompt or query")
    llm_response: str = Field(..., description="LLM or agent response")
    relevant_clause_ids: List[str] = Field(
        default_factory=list, description="Relevant clause/document IDs"
    )
    scores: Dict[str, Any] = Field(
        default_factory=dict, description="Scoring or metadata"
    )
    extra_context: Dict[str, Any] = Field(
        default_factory=dict, description="Any extra context or metadata"
    )
    summary: Optional[str] = Field(
        default=None, description="Summary of the memory event"
    )
