"""
domain/models.py

Domain models for clauses and their metadata.
These models are used throughout the ingestion pipeline and downstream
systems for type safety, validation, and clear data contracts.

Usage:
    from domain.models import Clause, ClauseMetaData
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


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
