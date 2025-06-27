"""
mcp_server/agents/base_agent.py

Abstract base class for all agents in the system to ensure their is a contract between this class implementors i.e inheritors and its callers
its a shared uderstanding of what the exposed methods do
so that basically when the other agent langchain or llamaindex custom class inherits from this abstract class then they are promising to follow te rules described by abstract base class i.e implementing/defining all the methods from the base class in their own way example abstract class of shape and inheritors class like rectangle, square, circle etc... all implementing abstractmethod of area their own respective versions

Enforces A2A/MCP compliance, message serialization, and core agent lifecycle.
Async-compatible

Usage example:
    from .base_agent import BaseAgent, JsonRpcAgentMixin, jsonrpc_method

    class MyAgent(BaseAgent, JsonRpcAgentMixin):
        def __init__(self):
            BaseAgent.__init__(self, "my-agent-v1")
            JsonRpcAgentMixin.__init__(self)

        @jsonrpc_method
        def invoke(self, input: dict, context: dict) -> dict:
            # main agent invocation
            # ... your logic ...
            return {"result": "ok"}

        @jsonrpc_method
        def stream(self, input: dict, context: dict) -> dict:
            # streaming call
            # ... your logic ...
            return {"result": "streaming"}

    # to dispatch a json rpc call
    agent = MyAgent()
    # check the agentcard
    print(agent.agent_card())
    request = {
        "jsonrpc": "2.0",
        "method": "invoke",
        "params": {"input": {...}, "context": {...}},
        "id": 1
    }
    response = agent.dispatch_jsonrpc(request)
    print(response)


"""

from typing import TypeVar, Optional, Generic, Dict, Any, Callable, Union, List
from datetime import datetime, timezone
from .message_a2aserializer import A2AMessageSerializable
from abc import ABC, abstractmethod
import logging
import inspect
import json
import asyncio

# --- Type variables for input/output message typ ---
InputType = TypeVar("InputType", bound=A2AMessageSerializable)
OutputType = TypeVar("OutputType", bound=A2AMessageSerializable)
ContextType = TypeVar(
    "ContextType"
)  # 📌 unbounded from AgentContext for flexiblity for agent that dont need context passing downstream


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
        config: Optional[
            Dict[str, Any]
        ] = None,  # every agent intake, assessment, action have access to context.config to alter the processing if dynamic config are provided from the end admin user from electron client
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.timestamp = timestamp
        # for opentelemetry tracing
        self.trace_id = trace_id
        self.span_id = span_id
        self.config = config


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

    @abstractmethod
    async def invoke(self, input: InputType, context: ContextType) -> OutputType:
        """
        Async processing core (must be implemented)
        """
        raise NotImplementedError("All agents must implement async invoke()")

    def stream(self, input: InputType, context: ContextType) -> OutputType:
        """
        Process input as a stream of partial responses (default non-streaming fallback)

        Override this in agents that support streaming.
        """
        self.logger.debug(f"Using invoke() fallback for streaming in{self.agent_id}")
        return self.invoke(input, context)

    async def stream(self, input: InputType, context: ContextType) -> OutputType:
        """
        Async streaming imple (override for streaming support)
        """
        self.logger.debug(f"Using invoke() fallback for streaming in {self.agent_id}")
        return await self.invoke(input, context)

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

    async def abort(self) -> None:
        """
        Async abort mech (override if needed)
        """
        self.logger.warning(f"Async abort not implemented for {self.agent_id}")

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


class JsonRpcError(Exception):
    """
    Base class for JSON-RPC errors
    """

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)  # pass err message to base Exception class
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self):
        err = {"code": self.code, "message": self.message}
        if self.data is not None:
            err["data"] = self.data
        # 📌 {"code": ..., "message": ..., "data": ...}
        return err


class JsonRpcParseError(JsonRpcError):
    def __init__(self, details: str):
        # 📌 reff: https://www.jsonrpc.org/specification#error_object
        super().__init__(-32700, f"Parse error: {details}")


class JsonRpcInvalidRequest(JsonRpcError):
    def __init__(self, details: str):
        super().__init__(-32600, f"Invalid request: {details}")


class JsonRpcInvalidParams(JsonRpcError):
    def __init__(self, details: str):
        super().__init__(-32602, f"Invalid params: {details}")


class JsonRpcMethodNotFound(JsonRpcError):
    def __init__(self, method: str):
        super().__init__(-32601, f"Method not found: {method}")


class JsonRpcInternalError(JsonRpcError):
    def __init__(self, details: str):
        super().__init__(-32603, f"Internal error: {details}")


class AgentCardMethod:
    """
    Metadata for a registered agent method for agent card/discoery and describing its capabl
    """

    def __init__(
        self,
        name: str,
        func: Callable,
        doc: str,
        signature: str,  # the function parameter signature
        is_async: bool = False,
    ):
        self.name = name
        self.func = func
        self.doc = doc
        self.signature = signature
        self.is_async = is_async


class JsonRpcAgentMixin:
    """
    Mixin for BaseAgent to support JSON-RPC 2.0 dispatch and agent card discovery to any base agent
    Async-compatible
    """

    def __init__(self):
        self._jsonrpc_methods: Dict[str, AgentCardMethod] = {}
        self._register_jsonrpc_methods()

    def _register_jsonrpc_methods(self):
        """
        Registers all sync and async public methods decorated with @jsonrpc_method as JSON-RPC callable
        """
        # only return members of object self that are method or async coroutines
        for name, method in inspect.getmembers(
            self,
            predicate=lambda m: inspect.ismethod(m) or inspect.iscoroutinefunction(m),
        ):
            # 📌 False default safely skips method that are not explicitely marked with _isjsonrpc_method if it does not exist
            if getattr(method, "_is_jsonrpc_method", False):
                # sig ex (x: int, y:int)
                sig = str(inspect.signature(method))
                doc = inspect.getdoc(method) or ""
                is_async = inspect.iscoroutinefunction(method)
                self._jsonrpc_methods[name] = AgentCardMethod(
                    name, method, doc, sig, is_async
                )

    def agent_card(self) -> Dict[str, Any]:
        """
        Returns the agent's "card": available JSON-RPC methods, signatures, and docstrings
        """
        return {
            "agent_id": getattr(self, "agent_id", None),
            "methods": {
                name: {
                    "signature": method.signature,
                    "doc": method.doc,
                }
                for name, method in self._jsonrpc_methods.items()
            },
        }

    @staticmethod
    def _jsonrpc_error_response(req_id: Any, error: JsonRpcError) -> Dict:
        return {"jsonrpc": "2.0", "error": error.to_dict(), "id": req_id}

    @staticmethod
    def _jsonrpc_success_response(req_id: Any, result: Any) -> Dict:
        return {"jsonrpc": "2.0", "result": result, "id": req_id}

    def _handle_jsonrpc_single(self, req: Dict) -> Optional[Dict]:
        """
        Handle a single JSON-RPC 2.0 request object
        """
        req_id = req.get("id", None)
        try:
            if req.get("jsonrpc") != "2.0":
                raise JsonRpcInvalidRequest("Invalid JSON-RPC version")
            if "method" not in req:
                raise JsonRpcInvalidRequest("Missing method")
            method_name = req["method"]
            params = req.get("params", {})

            # method: agent_card
            if method_name == "agent_card":
                result = self.agent_card()
                return self._jsonrpc_success_response(req_id, result)

            # method: Lookup
            if method_name not in self._jsonrpc_methods:
                raise JsonRpcMethodNotFound(method_name)

            method = self._jsonrpc_methods[method_name].func

            # some other Call method
            if isinstance(params, dict):
                # unpack the params pass it to method execute and stre result
                result = method(**params)  # **kwargs
            elif isinstance(params, list):
                result = method(*params)  # *args
            else:
                # safe fallback with no params passe and method executed
                result = method(params) if params is not None else method()

            return self._jsonrpc_success_response(req_id, result)
        except JsonRpcError as e:
            return self._jsonrpc_error_response(req_id, e)
        except Exception as e:
            return self._jsonrpc_error_response(req_id, JsonRpcInternalError(str(e)))

    async def _handle_jsonrpc_single(self, req: Dict) -> Optional[Dict]:
        """
        Async jsonrpc handler
        """
        req_id = req.get("id", None)
        try:
            if req.get("jsonrpc") != "2.0":
                raise JsonRpcInvalidRequest("Invalid JSON-RPC version")
            if "method" not in req:
                raise JsonRpcInvalidRequest("Missing method")
            method_name = req["method"]
            params = req.get("params", {})

            # method: agent_card
            if method_name == "agent_card":
                result = self.agent_card()
                return self._jsonrpc_success_response(req_id, result)

            # method: Lookup
            if method_name not in self._jsonrpc_methods:
                raise JsonRpcMethodNotFound(method_name)
            method = self._jsonrpc_methods[method_name]

            # Execute method with async awareness
            if method.is_async:
                result = (
                    await method.func(**params)
                    if isinstance(params, dict)
                    else (
                        await method.func(*params)
                        if isinstance(params, list)
                        else await method.func()
                    )
                )
            else:
                result = (
                    method.func(**params)
                    if isinstance(params, dict)
                    else (
                        method.func(*params)
                        if isinstance(params, list)
                        else method.func()
                    )
                )

            return self._jsonrpc_success_response(req_id, result)

        except Exception as e:
            return self._jsonrpc_error_response(req_id, JsonRpcInternalError(str(e)))

    def dispatch_jsonrpc(
        self, request_json: Union[str, Dict, List]
    ) -> Union[Dict, List[Dict]]:
        """
        Main JSON-RPC 2.0 dispatch entry point
        Handles single(str or Dict) and batch requests(List)

        Returns:
            a single response Dict or List of Dict responses
        """
        try:
            if isinstance(request_json, str):
                req = json.loads(request_json)
            else:
                req = request_json
        except Exception as e:
            return self._jsonrpc_error_response(None, JsonRpcParseError(str(e)))

        if isinstance(req, list):
            # if batch request
            if not req:
                return self._jsonrpc_error_response(
                    None, JsonRpcInvalidRequest("Empty batch")
                )
            #  📌 loop over req and process each request and store the result of each process in r as list of processed req
            return [
                r
                for r in (self._handle_jsonrpc_single(r) for r in req)
                if r is not None
            ]
        else:  # single req i.e dict/json payload
            return self._handle_jsonrpc_single(req)

    async def dispatch_jsonrpc(
        self, request_json: Union[str, Dict, List]
    ) -> Union[Dict, List[Dict]]:
        """
        Async jsonrpc batch request handler
        """
        try:
            if isinstance(request_json, str):
                req = json.loads(request_json)
            else:
                req = request_json
        except Exception as e:
            return self._jsonrpc_error_response(None, JsonRpcParseError(str(e)))

        if isinstance(req, list):
            # *(generated coroutines) * will unpack all coroutines produced by generator so that to pass multiple indv corutine objects as sep arguments to asyncio.gather
            # asyncio.gather(coroutine1,coroutine2,....)
            return await asyncio.gather(*(self._handle_jsonrpc_single(r) for r in req))
        else:
            return await self._handle_jsonrpc_single(req)


def jsonrpc_method(func):
    """
    Decorator to mark agent methds both sync and async as JSON-rpc callable
    """
    func._is_jsonrpc_method = True
    return func
