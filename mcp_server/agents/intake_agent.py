# mcp_server/agents/intake_agent.py

from .base_agent import (
    BaseAgent,
    JsonRpcAgentMixin,
    jsonrpc_method,
    AgentContext,
    AgentInvocationError,
)
from .intake_messages import IntakeInput, IntakeOutput
from datetime import datetime, timezone
import asyncio
import faker
from infrastructure.kafka.producer_singleton import kafka_producer
from utils.logger import get_logger

logger = get_logger("intake_agent")


class IntakeAgent(
    BaseAgent[IntakeInput, IntakeOutput, AgentContext], JsonRpcAgentMixin
):
    """
    Intake Agent that validates, enriches, and streams transactions
    Streaming is controlled by external registry and tools layer
    """

    def __init__(self):
        BaseAgent.__init__(self, "intake-agent-v1")
        JsonRpcAgentMixin.__init__(self)
        self._stream_tasks = {}  # {stream_id: asyncio.Task}
        self.fake = faker.Faker()

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
        }

    async def retrieve_prior_events(self, input: IntakeInput) -> list:
        # 🎈 qdrant lookup for prior similar events
        await asyncio.sleep(0.05)
        return [{"event_id": "prior1"}, {"event_id": "prior2"}]

    @jsonrpc_method
    async def invoke(self, input: IntakeInput, context: AgentContext) -> IntakeOutput:
        self.validate_input(input, context)
        enriched = self.enrich_transaction(input, context)
        prior_events = await self.retrieve_prior_events(input)
        return IntakeOutput(enriched, prior_events)

    async def _mock_stream_loop(self, stream_id: str, source: str, registry):
        """
        Background task: generates and publishes transactions while stream is active in registry.
        """
        while await registry.is_active(stream_id):
            txn = IntakeInput(
                txn_id=self.fake.uuid4(),
                amount=self.fake.pyfloat(left_digits=3, right_digits=2, positive=True),
                source=source,
            )
            context = AgentContext(
                request_id=self.fake.uuid4(),
                user_id="system",  # Or pass admin user if you want to track
                timestamp=datetime.now(timezone.utc),
            )
            output = await self.invoke(txn, context)
            enriched_data = output.enriched_txn
            enriched_data["prior_events"] = output.prior_events
            enriched_data["stream_id"] = stream_id
            try:
                await kafka_producer.produce("triageevents", enriched_data)
            except Exception as e:
                logger.error(f"Failed to publish to kafka: {e}")
            await asyncio.sleep(1)  # 1 event per second

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
