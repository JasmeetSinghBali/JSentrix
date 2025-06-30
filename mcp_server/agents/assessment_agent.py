"""
mcp_server/agents/assessment_agent.py
"""

from typing import Dict, List, Any
from datetime import datetime, timezone
from utils.logger import get_logger
from .base_agent import (
    BaseAgent,
    JsonRpcAgentMixin,
    AgentContext,
    AgentInvocationError,
    jsonrpc_method,
)
from application.retrievers.langchain_retriever import GraphMemoryRetriever
from .assessment_messages import AssessmentInput, AssessmentOutput
from domain.models import MemoryEvent
from domain.config_models import PriorityLevel
import uuid
from llama_index.core.schema import Document

from infrastructure.ingestion.forwarder import forward_event_to_streaming_hub
from infrastructure.redis_streams import RedisStreams

logger = get_logger("assessment_agent")


class AssessmentAgent(
    BaseAgent[AssessmentInput, AssessmentOutput, AgentContext], JsonRpcAgentMixin
):
    """
    Assessment Agent:
    - score & prioritize txns using business rules- amount thresholds, prior memory events eg fraud tags
    - retrieved context from langchain+neo4j custom retrv
    - streams high priority txn to ActionAgent
    """

    def __init__(self, action_agent=None):
        """
        Initialize AssessmentAgent with optional downstream action agent
        """
        BaseAgent.__init__(self, "assessment-agent-v1")
        JsonRpcAgentMixin.__init__(self)
        self.action_agent = action_agent
        # langchain retrv
        self.retriever = GraphMemoryRetriever()

    def validate_input(self, input: AssessmentInput, context: AgentContext):
        """
        Validate assessment input.

        - If `transaction` or `amount` is missing → raise AgentInvocationError (skips current txn).
        - If `prior_events` is None → fallback to [].

        Raises:
            AgentInvocationError: For incomplete or missing required input.
            📌 only skip the broken transaction and move to the next txn in _mock_stream_loop
        """
        if not input.transaction:
            raise AgentInvocationError("Missing transaction object", self.agent_id)
        if "amount" not in input.transaction:
            raise AgentInvocationError(
                "Transaction missing 'amount' field", self.agent_id
            )
        if input.prior_events is None:
            logger.warning("[Assessment] prior_events missing- defaulting to []")
            input.prior_events = []

    def _score_transaction(self, txn, prior_events: List[MemoryEvent], langchain_docs):
        """
        Score the transaction using minimal business rules.
        Considers fraud tags in MemoryEvents and amount threshold.

        Returns:
            int: Priority score (e.g. 90 = high risk, 40 = low risk)
        """
        try:
            amount = txn.get("amount", 0)

            # 🎈 here ml/llm custom rules could be used for now minimalistic rule
            # scans for tags key at top level and nested of extra_context
            # 🎈 though possibility of not passing i.e skipping potential voilating txns to the downstream action agent for analysis is their due to hardcoded business rules here
            # better way shud be to pass the medium and low priority txn directly to judge agent that way if judge agent make those transaction inconclusive then it can be send for manual review to the user ui where user could then either decide to freeze/flag the txn via invoking the action agent direct method from the ui itself.
            def _extract_tags(evt: MemoryEvent) -> List[str]:
                tags_top = getattr(evt, "tags", []) or []
                tags_extra = evt.extra_context.get("tags", []) or []
                # set to remove duplicates if any
                return list(set(tags_top + tags_extra))

            has_fraud_history = any(
                "fraud" in _extract_tags(evt) for evt in prior_events
            )
            if amount > 10000 or has_fraud_history:
                return 90
            if langchain_docs:
                return 70
            return 40
        except Exception as e:
            logger.error(f"❌ Error scoring transactions: {e}")
            return 0  # fallback score

    def _categorize_priority(self, score):
        if score >= 80:
            return PriorityLevel.HIGH
        elif score >= 50:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW

    @jsonrpc_method
    async def invoke(
        self, input: AssessmentInput, context: AgentContext
    ) -> AssessmentOutput:
        """
        Main A2A method to assess a transaction

        Steps:
            1. Retrieve hybrid context from Neo4j via LangChain
            2. Build dynamic metadata mapping for downstream agents
            3. Score the transaction using rules
            4. Return enriched output

        Returns:
            AssessmentOutput
        """
        config = context.config or {}
        assessment_type = config.get("assessment_type", "default")

        self.validate_input(input, context)
        # --- step1: hybrid retrieval using langchain retrv ---
        raw_query = f"Compliance check for {input.transaction.get("amount")} transfer from {input.transaction.get("source")}"
        langchain_docs = await self.retriever.async_get_relevant(
            raw_query, top_k=5, rescore=True
        )
        if not langchain_docs:
            logger.warning("❌ Langchain retrv failed")
            langchain_docs = []

        # --- step2: build dynamic metadata mapping ---
        # {
        #     "C001": {
        #         "clause_id": "C001",
        #         "title": "Data Transfer",
        #         "clause_type": "Prohibition",
        #         "source": "Policy A"
        #     },
        #     "C002": {
        #         "clause_id": "C002",
        #         "title": "Retention",
        #         "clause_type": "Obligation",
        #         "source": "Policy B"
        #     }
        # }...
        dynamic_metadata_by_clause_id = {
            doc.metadata["clause_id"]: dict(doc.metadata)
            for doc in langchain_docs
            if "clause_id" in doc.metadata
        }

        # --- step3: scoring and prioritization ---
        score = self._score_transaction(
            input.transaction, input.prior_events, langchain_docs
        )
        priority = self._categorize_priority(score)
        reasons = [f"Score {score} based on rules and retrieval"]

        # --- step4: conditional forward to ActionAgent or RedisStreams based on config priority and assessment_type ---
        # defaults config to high value txns in case priority not defined from the end user
        configured_priorities = config.get("priority", [PriorityLevel.HIGH])
        if isinstance(configured_priorities, list):
            configured_priorities = [
                PriorityLevel(p) if isinstance(p, str) else p
                for p in configured_priorities
            ]
        logger.debug(f"grabbed configured-priorities: {str(configured_priorities)}")
        output = AssessmentOutput(
            score=score,
            priority=priority,
            reasons=reasons,
            assessment_id=f"assess-{uuid.uuid4()}",
            # langchain doc--> llamaindex docs
            llamaindex_docs=[
                Document(text=doc.page_content, metadata=doc.metadata)
                for doc in langchain_docs
            ],
            dynamic_metadata=dynamic_metadata_by_clause_id,
            metadata={"stream_id": input.stream_id},
        )
        # 📌 Real-time forward to streaming hub
        await self._forward_with_fallback(output.to_dict(), input.stream_id)

        # 📌 foward to downstream action agent if the current txn priority is in configured priority set from the end user ui
        if priority in configured_priorities:
            if assessment_type == "default" and self.action_agent:
                # 🎈 uncomment this when implement action_agent.py
                # pass this as direct a2a message to action agent
                # await self.action_agent.invoke(
                #     output,
                #     context,
                # )
                pass
            elif assessment_type == "redistream":
                # produce output and context to the downstream action agent
                try:
                    redis_streams = RedisStreams()
                    await redis_streams.produce(
                        "assessed_events_stream",
                        {
                            "output": output.to_dict(),
                            "context": context.to_dict(),
                        },
                    )
                    # 🎈 NOTE- action_agent at __init__ shud register the consumer via the bg worker reff: mcp_server/workers/assessed_events_stream_worker.py
                    # below shud be in action agent __init__
                    # redis_streams = RedisStreams()
                    # async for msg_id, data in assessed_events_consumer_worker(
                    #     consumer=consumer_name,
                    #     redis_streams=redis_streams
                    # ):
                    #     await take_action(data)
                    #     await redis_streams.ack("assessed_events_stream", "action_agents", msg_id)
                    # await redis_streams.close()
                    # --------------------------------------------------
                finally:
                    await redis_streams.close()

            else:
                logger.warning(f"Unknown assessment_type: {assessment_type}. Skipping")
        else:
            logger.info(
                f"Txn priority {priority} not in configured filter {configured_priorities}. Skipping downstream send."
            )
        return output

    async def _forward_with_fallback(self, data: dict, stream_id: str):
        """
        Forward enriched output to Redis Stream (fallback enabled)

        Flow:
        Agent → forward_event_to_streaming_hub(event) 🚀
           → Kafka "ingest_topic" (ONLY used for streaming-hub dispatch)
               → Go streaming-hub
                   → Redis Pub/Sub
                       → WebSocket clients
        """
        event_payload = {
            "event": "2️⃣[AssessmentAgent]",
            "message": "Real-time assessment event",
            "stream_id": stream_id,  # 📌 Critical for targeted fanout
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",  # ISO 8601 UTC
            "agent": "assessment-agent",  # 💫 Agent identifier for filtering the events in ui client or telemetry logs
            "level": "info",  # log severity
        }
        success = await forward_event_to_streaming_hub(event_payload)
        if not success:
            logger.warning(
                f"[ForwardWithFallback] Event failed to forward and was sent to DLQ: stream_id={stream_id}"
            )
