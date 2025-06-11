"""
mcp_server/agents/base_agent.py

Abstract base class for all agents in the system to ensure their is a contract between this class implementors i.e inheritors and its callers
its a shared uderstanding of what the exposed methods do
so that basically when the other agent langchain or llamaindex custom class inherits from this abstract class then they are promising to follow te rules described by abstract base class i.e implementing/defining all the methods from the base class in their own way example abstract class of shape and inheritors class like rectangle, square, circle etc... all implementing abstractmethod of area their own respective versions

Enforces A2A/MCP compliance, message serialization, and core agent lifecycle.

Usage example:
class IntakeAgent(BaseAgent):
    def __init__(self):
        super().__init__("intake-agent-v1")
        self._active = False

    def invoke(self, input, context):
        self._active = True
        try:
            # Processing logic...
            return output
        finally:
            self._active = False

    def abort(self):
        super().abort()  # Logs warning
        if self._active:
            # Actual cleanup logic
            self._active = False
"""

from typing import TypeVar, Optional, Generic, Dict, Any
from datetime import datetime, timezone
from .message_a2aserializer import A2AMessageSerializable
from abc import ABC, abstractmethod
import logging

# --- Type variables for input/output message typ ---
InputType = TypeVar("InputType", bound=A2AMessageSerializable)
OutputType = TypeVar("OutputType", bound=A2AMessageSerializable)
ContextType = TypeVar("ContextType")


class AgentContext(A2AMessageSerializable):
    """
    MCP-compliant context for agent execution
    carriess metadata needed for A2A communication and protocol compliances
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


class BaseAgent(ABC, Generic[InputType, OutputType, ContextType]):
    """
    Abstract base class for all agents in the system
    Enforces A2A/MCP compliance and provides core agent lifecycle methods

    Subclasses must implement:
    - invoke(): Core agent processing logic

    Subclasses may override:
    - stream(): For streaming capabilities
    - abort(): For abortable operations

    Usage:
    class MyAgent(BaseAgent[MyInput, MyOutput, MyContext]):
        def invoke(self, input: MyInput, context: ContextType) -> MyOutput:
            ...
    """

    def __init__(self, agent_id: str):
        """
        Args:
            agent_id: Unique identifier for this agent type (e.g., "intake-agent-v1")
        """
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"agent: {agent_id}")
        self._abort_flag = False

    @abstractmethod
    def invoke(self, input: InputType, context: ContextType) -> OutputType:
        """
        Process an input message and return a response

        Args:
            input: A2A-serializable input message
            context: Execution context with MCP metadata

        Returns:
            A2A-serializable output message

        Raises:
            AgentInvocationError: For business logic failures
            AgentFatalError: For unrecoverable errors
        """
        raise NotImplementedError("All agents must implement invoke()")

    def stream(self, input: InputType, context: ContextType) -> OutputType:
        """
        Process input as a stream of partial responses (default non-streaming fallback)

        Override this in agents that support streaming.
        """
        self.logger.debug(f"Using invoke() fallback for streaming in{self.agent_id}")
        return self.invoke(input, context)

    def abort(self) -> None:
        """
        Request graceful termination of current operation (default no-op).

        Override in abortable agents to implement actual cleanup.

        Usage:
            class AnalysisAgent(BaseAgent):
                def abort(self):
                    raise NotSupportedError(
                        "This agent cannot be aborted",
                        self.agent_id
                    )
        """
        self.logger.warning(f"Abort requested but not implemented for {self.agent_id}")

    def get_status(self) -> Dict[str, Any]:
        """
        Return current agent status for monitoring
        must include MCP-required fields
        """
        return {
            "agent_id": self.agent_id,
            "is_healthy": True,
            "last_active": datetime.now(timezone.utc).isoformat(),
            "supports_abort": False,  # override in abortable agents
        }

    def __repr__(self):
        return f"<BaseAgent {self.agent_id}"


# ---- Possible core exceptions ----
class AgentError(Exception):
    """
    Base class for all agent exception
    """

    def __init__(self, message: str, agent_id: str):
        super().__init__(message)
        self.agent_id = agent_id


class AgentInvocationError(AgentError):
    """
    Recoverable error during agent invocation
    """


class AgentFatalError(AgentError):
    """
    Unrecoverable error requiring agent restart
    """


class NotSupportedError(AgentError):
    """
    Raised when agent doesn't support requested operation
    """
