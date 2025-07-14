"""
mcp_server/agents/assessment_messages.py

Usage:
        context.config:
        allowed_priorities = context.config.get("priority", ["HIGH"]) # defaults to HIGH else passed priority by end user
        # Then filter prior events:
        filtered_events = [event for event in prior_events if event.priority in allowed_priorities]
        # further pass these filtered_events only to downstream action llamaindex agent for llm inference and further actions
        or
        in assessment_agent.py
        def filter_prior_events(prior_events: List[MemoryEvent], context: AgentContext) -> List[MemoryEvent]:
                allowed = context.config.get("priority", ["HIGH"])
                return [evt for evt in prior_events if evt.priority in allowed]
"""

from .message_a2aserializer import A2AMessageSerializable
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from domain.models import MemoryEvent
from domain.config_models import PriorityLevel
from .base_agent import AgentContext
from llama_index.core.schema import Document


class AssessmentInput(A2AMessageSerializable):
    """
    A2A-compliant input for assessment agent containing:
    - Enriched transaction from intake
    - relevant prior events
    - cache-aware short circuiting fields
    """

    def __init__(
        self,
        transaction: Dict[str, Any],
        prior_events: List[MemoryEvent],
        stream_id: str,
        context: Optional[AgentContext] = None,
        skip_assessment: bool = False,
        cache_event: Optional[dict] = None,
    ):
        self.transaction = transaction
        self.prior_events = prior_events
        self.stream_id = stream_id
        self.context = context or AgentContext(
            request_id="n/a",
            user_id="system",
            timestamp=datetime.now(timezone.utc),
        )
        self.skip_assessment = skip_assessment
        self.cache_event = cache_event


class AssessmentOutput(A2AMessageSerializable):
    """
    A2A-compliant output from AssessmentAgent:
    - Priority score and level
    - Reasoning for decision
    - LlamaIndex-ready document payload (text + metadata)
    - Clause-level structured metadata
    - Original transaction & prior memory events (passed to ActionAgent)
    - Agent context metadata (stream_id, etc.)
    """

    def __init__(
        self,
        score: float,
        priority: PriorityLevel,
        reasons: List[str],
        assessment_id: str,
        transaction: Dict[str, Any],
        prior_events: List[MemoryEvent],
        llamaindex_docs: List,  # Accepts both dicts and document objects
        dynamic_metadata: Dict[str, Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ):
        self.score = score
        self.priority = priority  # "LOW", "MEDIUM", "HIGH"
        self.reasons = reasons
        self.assessment_id = assessment_id
        self.transaction = transaction
        self.prior_events = prior_events
        # convrt dicts to Document objects if needed
        self.llamaindex_docs = [
            doc if isinstance(doc, Document) else Document(**doc)
            for doc in llamaindex_docs
        ]
        self.dynamic_metadata = dynamic_metadata  # {"C001": {...}, ...}
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
