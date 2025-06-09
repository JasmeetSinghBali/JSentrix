"""
mcp_server/agents/base_agent.py

Abstract base class for all agents in the system to ensure their is a contract between this class implementors i.e inheritors and its callers
its a shared uderstanding of what the exposed methods do
so that basically when the other agent langchain or llamaindex custom class inherits from this abstract class then they are promising to follow te rules described by abstract base class i.e implementing/defining all the methods from the base class in their own way example abstract class of shape and inheritors class like rectangle, square, circle etc... all implementing abstractmethod of area their own respective versions

Enforces A2A/MCP compliance, message serialization, and core agent lifecycle.
"""

from typing import TypeVar, Optional
from datetime import datetime
from .message_a2aserializer import A2AMessageSerializable

# --- Type variables for input/output message typ ---
InputType = TypeVar("InputType", bound=A2AMessageSerializable)
OutputType = TypeVar("OutputType", bound=A2AMessageSerializable)
ContextType = TypeVar("ContextType")


class AgentContext(A2AMessageSerializable):
    """
    MCP-compliant context for agent execution
    carriess metadata needed for A2A communication and protocol compliance
    """

    def __init__(
        self,
        request_id: str,
        user_id: str,
        timestamp: datetime,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.timestamp = timestamp
        # for opentelemetry tracing
        self.trace_id = trace_id
        self.span_id = span_id
