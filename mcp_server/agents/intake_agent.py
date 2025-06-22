# mcp_server/agents/intake_agent.py

from typing import Dict, List, Any
from .base_agent import (
    BaseAgent,
    JsonRpcAgentMixin,
    jsonrpc_method,
    AgentContext,
    AgentInvocationError,
    AgentFatalError,
    AgentError,
)
from .intake_messages import IntakeInput, IntakeOutput
from datetime import datetime, timezone
import asyncio
import faker

from utils.logger import get_logger
from utils.embedding_utils import get_langchain_embedding_model

from application.retrievers.memory_event_retriever import MemoryEventRetriever
from infrastructure.memory_event_repository import MemoryEventRepository

from infrastructure.ingestion.forwarder import forward_event_to_streaming_hub

from domain.models import MemoryEvent


logger = get_logger("intake_agent")


class IntakeAgent(
    BaseAgent[IntakeInput, IntakeOutput, AgentContext], JsonRpcAgentMixin
):
    """
    Intake Agent that validates, enriches, streams and routes transactions
    - Streams to kafka/electron UI
    - Passes enriched txn + prior events to Langchain Assessment Agent
    """

    def __init__(self, assessment_agent=None):
        BaseAgent.__init__(self, "intake-agent-v1")
        JsonRpcAgentMixin.__init__(self)
        self._stream_tasks = {}  # {stream_id: asyncio.Task}
        self.fake = faker.Faker()

        self.embedding_model = get_langchain_embedding_model()
        self.retriever = MemoryEventRetriever(MemoryEventRepository())
        # 🎈 to build and setup assessment_agent langchain for next phase later
        self.assessment_agent = assessment_agent

    def validate_input(self, input: IntakeInput, context: AgentContext):
        if not input.txn_id or input.amount < 0:
            raise AgentInvocationError("Invalid transaction input", self.agent_id)

    def enrich_transaction(self, input: IntakeInput, context: AgentContext) -> dict:
        return {
            "txn_id": input.txn_id,
            "amount": input.amount,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": input.source,
            "metadata": input.metadata,
            # contextual metadata agentcontext needed for a2a communication
            "context": {
                "request_id": context.request_id,
                "user_id": context.user_id,
                "agent_id": self.agent_id,
                "trace_id": context.trace_id or "N/A",
                "span_id": context.span_id or "N/A",
            },
        }

    async def retrieve_prior_events(self, enriched_txn: dict) -> List[MemoryEvent]:
        """
        Retrieve relevant prior memory events using vector embedded prompt query + metadata filtering
        """
        prompt = (
            f"Async compliance audit for {enriched_txn['amount']} transfer "
            f"from {enriched_txn['source']} on {enriched_txn['timestamp']}"
        )
        try:
            # async embedding
            query_vector = await asyncio.to_thread(
                self.embedding_model.embed_query, prompt
            )
            # 📌 qdrant lookup for prior similar events
            prior_events = await self.retriever.async_get_events(
                query_vector=query_vector,
                filters={"source": enriched_txn["source"]},
                top_k=5,
            )
            logger.info(
                f"\n[Intake] Retrieved prior_events qdrant lookup {len(prior_events)} memories"
            )
            # Return raw Pydantic models – let A2AMessageSerializable handle serialization later
            return prior_events
        except Exception as e:
            logger.error(f"[Intake] prior events retrieval failed: {e}")
            return []

    @jsonrpc_method
    async def invoke(self, input: IntakeInput, context: AgentContext) -> IntakeOutput:
        """
        returns an A2A-safe, forwardable, and serializable object
        """
        self.validate_input(input, context)
        enriched = self.enrich_transaction(input, context)
        prior_events = await self.retrieve_prior_events(enriched)
        return IntakeOutput(enriched, prior_events)

    async def _mock_stream_loop(self, stream_id: str, source: str, registry):
        """
        Background task:
        Generates and forwards/publishes mock transactions while the stream is active in registry.
        Each enriched transaction is passed to streaming hub and downstream assessment agent.
        """
        try:
            while await registry.is_active(stream_id):
                try:
                    # fake/mock txn generator
                    txn = IntakeInput(
                        txn_id=self.fake.uuid4(),
                        amount=self.fake.pyfloat(
                            left_digits=3, right_digits=2, positive=True
                        ),
                        source=source,
                    )
                    # 📌 custom agent context can be extended here
                    context = AgentContext(
                        request_id=self.fake.uuid4(),
                        user_id="system",  # 📌 Or pass admin/user actual id in case the agent is directly invoked from client side
                        timestamp=datetime.now(timezone.utc),
                    )
                    # invoke with error wrapper
                    output = await self._safe_invoke(txn, context)

                    # 🎈 forward to langchain assessment agent here so that assesment can also happen event by event as they are consume and processed by intake agent
                    # enriched_data now looks like {enriched_txn: {},prior_events: [MemoryEvent, MemoryEvent],stream_id: ""}
                    # NOTE- assessment_agent.invoke() shud be implemented using A2A architecture (i.e., it either:
                    # uses A2AMessageSerializable or
                    # serializes the payload using to_dict() or to_json() internally),
                    # so that _serialize_value() in A2AMessageSerializable will automatically convert the MemoryEvent instances using .model_dump() when it's serialized — so no need to do it manually anymore.
                    # await self.assessment_agent.invoke(enriched_data)

                    # force serialization before pushing to external kafka/ui
                    # Enrich and forward
                    # output.to_dict() => {
                    # "enriched_txn": {...},
                    # "prior_events": [dict, dict, ...]
                    # }
                    # NOTE- When leaving the agent boundary (Kafka, socket, DB, HTTP): use .to_dict() or .to_json()
                    # When staying inside the agent system (A2A calls): just pass the object directly
                    enriched_data = (
                        output.to_dict()
                    )  # this includes .model_dump() on MemoryEvent
                    enriched_data["stream_id"] = stream_id

                    # --- Forward to streaming-hub via forwarder event by event ---
                    await self._forward_with_fallback(enriched_data, stream_id)

                except AgentFatalError as e:
                    logger.critical(f"[Intake] Fatal error in stream {stream_id}: {e}")
                    await self._handle_fatal_error(stream_id, e, registry)
                    break
                except Exception as e:
                    logger.error(
                        f" [Intake] Recoverable error in stream {stream_id}: {e}"
                    )
                    await asyncio.sleep(1)  # Backoff before retry
                finally:
                    await asyncio.sleep(1)  # 1 event/txn per second
        except asyncio.CancelledError:
            logger.info(f"[Intake] Stream loop {stream_id} cancelled")
        except Exception as e:
            logger.critical(f"[Intake] Unhandled error in stream loop {stream_id}: {e}")

    @jsonrpc_method
    async def stream(self, input: dict, context: AgentContext) -> dict:
        """
        Start streaming mock transactions for a given stream_id and source.
        Args:
            input: dict with keys 'stream_id' (str), 'source' (str, optional)
        """
        stream_id = input.get("stream_id")
        source = input.get("source", "faker")
        registry = input.get("registry")  # Should be passed in by the tool layer

        if not stream_id or not registry:
            raise AgentInvocationError("stream_id and registry required", self.agent_id)
        if stream_id in self._stream_tasks:
            return {"result": "Streaming already running for this stream_id."}

        # Start background streaming task
        task = asyncio.create_task(self._mock_stream_loop(stream_id, source, registry))
        self._stream_tasks[stream_id] = task
        return {
            "result": "Streaming started.",
            "stream_id": stream_id,
            "source": source,
        }

    @jsonrpc_method
    async def abort(self, input: dict, context: AgentContext) -> dict:
        """
        Stop streaming for a given stream_id.
        Args:
            input: dict with key 'stream_id' (str)
        """
        stream_id = input.get("stream_id")
        if not stream_id:
            raise AgentInvocationError("stream_id required", self.agent_id)
        task = self._stream_tasks.pop(stream_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return {"result": "Streaming aborted.", "stream_id": stream_id}
        else:
            return {
                "result": "No active stream for this stream_id.",
                "stream_id": stream_id,
            }

    async def _safe_invoke(
        self, txn: IntakeInput, context: AgentContext
    ) -> IntakeOutput:
        """Invoke with error conversion"""
        try:
            return await self.invoke(txn, context)
        except AgentError as e:
            raise  # Re-raise known agent errors
        except Exception as e:
            # Convert unexpected errors to agent errors
            raise AgentInvocationError(
                f"Unexpected invocation error: {str(e)}", self.agent_id
            ) from e

    async def _forward_with_fallback(self, data: dict, stream_id: str):
        """Forward with retry and fallback handling"""
        try:
            await forward_event_to_streaming_hub(
                {
                    "event": "transaction",
                    "message": "Mock transaction event",
                    "stream_id": stream_id,
                    "data": data,
                }
            )
        except Exception as e:
            logger.error(f"Critical forwarding error: {e}")
            # 🎈 Implement dead-letter queue or other recovery
            # await self._store_in_fallback_queue(data)

    async def _handle_fatal_error(
        self, stream_id: str, error: AgentFatalError, registry
    ):
        """Handle unrecoverable errors"""
        # 1. Log critical error
        logger.critical(f"Terminating stream {stream_id} due to fatal error")

        # 2. 🎈 Notify event to electron ui via  new event forward_event_to_streaming_hub

        # 3. Remove from registry
        if await registry.is_active(stream_id):
            await registry.remove(stream_id)

        # 4. Cancel background task
        if task := self._stream_tasks.pop(stream_id, None):
            task.cancel()
