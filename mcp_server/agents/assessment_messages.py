"""
mcp_server/agents/assessment_messages.py
"""

from .message_a2aserializer import A2AMessageSerializable
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from domain.models import MemoryEvent
from .base_agent import AgentContext
from enum import Enum


class AssessmentInput(A2AMessageSerializable):
    """
    A2A-compliant input for assessment agent containing:
    - Enriched transaction from intake
    - relevant prior events
    """

    def __init__(
        self,
        transaction: Dict[str, Any],
        prior_events: List[MemoryEvent],
        stream_id: str,
        context: Optional[AgentContext] = None,
    ):
        self.transaction = transaction
        self.prior_events = prior_events
        self.stream_id = stream_id
        self.context = context or AgentContext(
            request_id="n/a", user_id="system", timestamp=datetime.now(timezone.utc)
        )


# 🎈FEATURE-POSS: Later this cud be used as dynamic config passed by end user in payload at time of calling streminges for that stream from electron to say include medium prior events also along with the default high prior one's
# 🎈 a modal with source, priority selection could be done before calling the streaminges tool from the electron client by the admin
class PriorityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AssessmentOutput(A2AMessageSerializable):
    """
    A2A compliant output for assessment agent contains:
    - Priority score
    - categorized priority
    - assessment metadata
    """

    def __init__(
        self,
        score: float,
        priority: PriorityLevel,
        reasons: List[str],
        assessment_id: str,
        metadata: Dict[str, Any] = None,
    ):
        self.score = score
        self.priority = priority  # "LOW", "MEDIUM", "HIGH"
        self.reasons = reasons
        self.assessment_id = assessment_id
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
