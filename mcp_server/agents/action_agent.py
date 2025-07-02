"""
mcp_server/agents/action_agent.py
"""

from typing import List
from .base_agent import BaseAgent, JsonRpcAgentMixin, AgentContext, jsonrpc_method
from .action_messages import ActionInput, ActionOuput, DecisionLevel
from utils.logger import get_logger
from application.retrievers.llamaindex_retriever import (
    async_get_llamaindex_query_engine_from_docs,
)
import json
import uuid
from datetime import datetime, timezone
from infrastructure.ingestion.forwarder import forward_event_to_streaming_hub
from domain.models import MemoryEvent
from llama_index.core import Document

logger = get_logger("action_agent")


class ActionAgent(BaseAgent[ActionInput, ActionOuput, AgentContext], JsonRpcAgentMixin):
    """
    Action Agent:
    - accepts high priority txns(default) or config.priority member txns from assessment agent
    - performs deep LLM inference using LlamaIndex query engine with post node processors
    - flags violating txns
    - forwards inconclusive "ND" or "NO" decisions to Judge agent for downstream for 2nd level of inference
    """

    def __init__(self, judge_agent=None):
        BaseAgent.__init__(self, "action-agent-v1")
        JsonRpcAgentMixin.__init__(self)
        self.judge_agent = judge_agent

    def _build_compliance_query(self, transaction: dict) -> str:
        """
        Build a minimal prompt grounded only in the transaction
        All additional context like prior_events is handled by the retriever (not the prompt) to mitigate overflowing context window of llm
        """
        txn_block = json.dumps(transaction, indent=4)

        return f"""
        You are a compliance agent with access to relevant regulatory clauses.

        Transaction:
        {txn_block}

        Instructions:
        1. Retrieve relevant clauses and prior decisions from memory/context.
        2. Evaluate whether this transaction violates any of those clauses.
        3. Respond strictly with: YES / NO / ND.
        Include a short justification in natural language.
        """

    @jsonrpc_method
    async def invoke(self, input: ActionInput, context: AgentContext) -> ActionOuput:

        assessment_type = context.config.get("assessment_type", "default")

        if assessment_type == "redistream":
            # 🎈 all the step 1,2,3 and 4 of direct a2a messageing default assessment_type shud now be done inside this block where the consumer is consuming these messages
            # 🎈 register the consumer for assessed_events_stream via the bg worker reff: mcp_server/workers/assessed_events_stream_worker.py
            # redis_streams = RedisStreams()
            # async for msg_id, data in assessed_events_consumer_worker(
            #     consumer=consumer_name,
            #     redis_streams=redis_streams
            # ):
            #     await take_action(data)
            #     await redis_streams.ack("assessed_events_stream", "action_agents", msg_id)
            # await redis_streams.close()
            return action_output

        # 📌 default a2a message passed from assessment agent
        logger.info(
            f"[ActionAgent] Recieve assessment: {input.assessment_output.assessment_id}"
        )

        # ---1. Prepare LlamaIndex query engine with augmented (txn+clause docs + prior memory) ---
        # base docs actually contains the relevant clauses from neo4j passed from the assessment agent
        base_docs = input.assessment_output.llamaindex_docs
        dynamic_metadata = input.assessment_output.dynamic_metadata
        prior_events = input.assessment_output.prior_events

        # new list to avoid mutating original
        llamaindex_docs = list(base_docs)

        for evt in prior_events:
            try:
                content = f"""
                Agent: {evt.agent_name}
                Timestamp: {evt.timestamp}
                Prompt: {evt.prompt}
                Response: {evt.llm_response}
                Extra Context: {json.dumps(evt.extra_context, indent=2)}
                """
                metadata = {
                    "source": "prior_event",
                    "agent_name": evt.agent_name,
                    "timestamp": str(evt.timestamp),
                }
                doc = Document(text=content, metadata=metadata)
                # 📌 both regulatory clauses(relevant clauses from assessment agent) + memory-based prior agent responses are embedded, indexed, and searchable by the LlamaIndex query engine during compliance evaluation
                llamaindex_docs.append(doc)
            except Exception as e:
                logger.warning(f"Failed to convert prior_event to Document: {e}")

        # --- 2. Init the query engine
        query_engine = async_get_llamaindex_query_engine_from_docs(
            docs=llamaindex_docs, dynamic_metadata_by_clause_id=dynamic_metadata
        )

        # ---3. Llamaindex processing & LLM inference and analysis
        transaction = input.assessment_output.transaction
        structured_query = self._build_compliance_query(transaction)

        response = query_engine.query(structured_query)

        if response is None:
            logger.warning("LlamaIndex query returned None!")
            decision = DecisionLevel.ND
            raw_response = "Inference failed"
        else:
            raw_response = str(getattr(response, "response", response))
            raw_upper = raw_response.upper()
            if "YES" in raw_upper:
                decision = DecisionLevel.YES
            elif "NO" in raw_upper:
                decision = DecisionLevel.NO
            else:
                decision = DecisionLevel.ND

        source_nodes = [
            {"metadata": node.metadata}
            for node in getattr(response, "source_nodes", [])
        ]

        action_output = ActionOuput(
            action_id=f"action-{uuid.uuid4()}",
            decision=decision,
            raw_response=raw_response,
            source_nodes=source_nodes,
            context=input.context,
        )

        # ---3. Flag txn and notify UI as action agent action if decision is YES ---
        # 📌 here additional freeze txn or other autonomoous action cud be performed
        if decision == DecisionLevel.YES:
            await self._forward_flagged_txn(
                action_output.to_dict(),
                input.assessment_output.metadata.get("stream_id", "NotDefined"),
            )

        # ---4. Forward NO/ND to judge agent ---
        elif decision in [DecisionLevel.NO, DecisionLevel.ND]:
            await self._forward_to_judge(action_output)

        # ---5. 🎈 Store MemoryEvent as needed maybe both yes and no decisions (Phase 7) ---
        # if decision == DecisionLevel.YES:
        #     await self.memory_agent.store_event(...)

        return action_output

    async def _forward_flagged_txn(self, data: dict, stream_id: str):
        """
        Forward flagged txn to streaming hub for UI alert
        """
        event = {
            "event": "3️⃣[ActionAgent]",
            "message": f"🚨 Action Taken: {data.decision}",
            "stream_id": stream_id,
            "data": data,
            "flagged": True,  # the streaming-hub event dto shud be sync with optional flagged key
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "agent": "action-agent",
            "level": "warn",
        }
        success = await forward_event_to_streaming_hub(event)
        if not success:
            logger.warning(
                f"[ForwardWithFallback]❌ Event failed to forward and was sent to DLQ: stream_id={stream_id}"
            )

    async def _forward_to_judge(self, output: ActionOuput):
        """
        Send ND/NO txns to downstream judge agent
        Replace this stub with A2A or RedisStream logic in Phase 6
        """
        logger.info(
            f"[ActionAgent] Forwarding to JudgeAgent: decision={output.decision}"
        )
        # 🎈 update this to pass ND/NO txn to judge agent
        # Example RedisStreams publish for judge agent or await judge_agent.invoke(output)
        # await self.judge_agent.invoke(output, context)
