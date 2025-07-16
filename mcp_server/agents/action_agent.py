"""
mcp_server/agents/action_agent.py
"""

import asyncio
from typing import List
from .base_agent import BaseAgent, JsonRpcAgentMixin, AgentContext, jsonrpc_method
from .action_messages import ActionInput, ActionOutput, DecisionLevel
from .assessment_messages import AssessmentOutput

from utils.logger import get_logger
from utils.embedding_utils import get_langchain_embedding_model
from utils.summarizer import T5Summarizer

from application.retrievers.llamaindex_retriever import (
    async_get_llamaindex_query_engine_from_docs,
)
import json
import uuid
from datetime import datetime, timezone

from domain.models import MemoryEvent
from domain.config_models import StreamingConfig

from llama_index.core import Document

from infrastructure.ingestion.forwarder import forward_event_to_streaming_hub
from infrastructure.redis_analysis_counter import analysis_counter_registry
from infrastructure.redis_streams import RedisStreams
from infrastructure.memory_event_repository import MemoryEventRepository

from workers.task_registry import task_registry
from workers.assessed_events_stream_worker import (
    assessed_events_consumer_worker,
)

logger = get_logger("action_agent")


class ActionAgent(
    BaseAgent[ActionInput, ActionOutput, AgentContext], JsonRpcAgentMixin
):
    """
    Action Agent:
    - accepts high priority txns(default) or config.priority member txns from assessment agent
    - performs deep LLM inference using LlamaIndex query engine with post node processors
    - flags violating txns
    - forwards inconclusive "ND" or "NO" decisions to Judge agent for downstream for 2nd level of inference
    """

    def __init__(
        self,
        judge_agent=None,
        memory_event_repository: MemoryEventRepository = None,
        embedding_model=None,
        summarizer=None,
    ):
        BaseAgent.__init__(self, "action-agent-v1")
        JsonRpcAgentMixin.__init__(self)
        self.judge_agent = judge_agent
        self._final_event_sent = set()
        self._final_event_lock = asyncio.Lock()

        # 🎈 maybe inject at time of the instantiation i.e inside agentGraph when called under streaming tools or omit it and let the action agent __init__ handle this
        self.memory_event_repository = (
            memory_event_repository or MemoryEventRepository()
        )
        self.embedding_model = embedding_model or get_langchain_embedding_model()
        self.summarizer = summarizer or T5Summarizer()

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

    async def _cleanup_final_event_flag(self, stream_id: str, delay: int = 600):
        await asyncio.sleep(delay)
        async with self._final_event_lock:
            self._final_event_sent.discard(stream_id)

    async def _emit_final_post_abort_event(self, stream_id: str):
        async with self._final_event_lock:
            if (
                stream_id in self._final_event_sent
            ):  # skip re-emitting of final event for the stream_id that was already sent earlier
                return
            self._final_event_sent.add(stream_id)
        # 📌 Register cleanup with global task manager
        task_registry.add(self._cleanup_final_event_flag(stream_id))
        event = {
            "event": "3️⃣[ActionAgent]",
            "message": "✅ Final compliance decision(s) complete (post-abort)",
            "stream_id": stream_id,
            "post_abort": True,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "agent": "action-agent",
            "level": "info",
        }
        success = await forward_event_to_streaming_hub(event)
        if not success:
            logger.warning(
                f"[FinalPostAbort]❌ Could not notify UI of final post-abort event: Stream ID: {stream_id}"
            )

    async def _store_memory_event_async(
        self, memory_event: MemoryEvent, embedding: list
    ):
        try:
            await self.memory_event_repository.store(memory_event, embedding)
            logger.info(
                f"[MemoryEvent] Stored event for txn_id={memory_event.extra_context.get('txn_id')} decision={memory_event.llm_response[:10]}..."
            )
        except Exception as e:
            logger.error(f"[MemoryEvent] Failed to store event: {e}")

    # ✅ LLM-heavy logic of inferenece and compliance as fire and forget bg task
    async def _handle_llamaindex_analysis(
        self, input: ActionInput, context: AgentContext
    ):
        """
        Handles llm heavy inference and compliance fire and forget
        continues even after stream has ended i.e abortinges called and stream and agent graph registery has been updated
        """
        registry = context.registry[0] if context and context.registry else None
        try:
            ao = input.assessment_output
            if isinstance(ao, dict):
                stream_id = ao.get("metadata", {}).get("stream_id", "NotDefined")
            else:
                stream_id = getattr(ao, "metadata", {}).get("stream_id", "NotDefined")

            # 🎈 better to have a configurable new key as cache: True that end user can send from ui if True then this cache short circuiting else normal flow
            # 🎈 CASE: if cache_hit then skip all inference steps for this txn and just emit compliance in progress and decision event so that the final abort event can be emitted accordingly and the ui can then cut off the websocket connection from its side
            metadata = (
                ao.metadata if hasattr(ao, "metadata") else ao.get("metadata", {})
            )
            is_cache_hit = metadata.get("source") == "cache"
            cache_event = metadata.get("cache_event", {})
            if is_cache_hit and cache_event:
                # ✅ Skip sending any intermediate UI events like "in progress" or "action taken"
                # Only decrement the analysis counter and store the memory event

                # Store MemoryEvent with source="cache"
                memory_event = MemoryEvent(
                    user_id=getattr(context, "user_id", None),
                    agent_name="action-agent",
                    prompt="CACHE_HIT",
                    llm_response=cache_event.get("llm_response", ""),
                    decision=cache_event.get("decision", "CACHE"),
                    original_transaction=ao.transaction,
                    relevant_clause_ids=cache_event.get("relevant_clause_ids", []),
                    metadata=cache_event.get("metadata", {}),
                    extra_context={
                        "stream_id": stream_id,
                        "cache_event_id": cache_event.get("event_id"),
                        "source": "cache",
                    },
                    summary="Cache hit: decision reused, no LLM analysis.",
                    source="cache",
                    llm_confidence=cache_event.get("llm_confidence"),
                    user_feedback=cache_event.get("user_feedback"),
                )
                # Use a zeroed embedding or retrieve the original one if needed
                embedding = [0.0] * self.memory_event_repository.vector_size
                task_registry.add(
                    self.memory_event_repository.store(memory_event, embedding)
                )

                # Just decrement the counter
                count = await analysis_counter_registry.decr(stream_id)
                if count == 0:
                    await self._emit_final_post_abort_event(stream_id=stream_id)
                    await analysis_counter_registry.reset(stream_id)
                return  # Early exit; skip the rest

            # ---1. Prepare LlamaIndex query engine with augmented (txn+clause docs + prior memory) ---
            base_docs = (
                input.assessment_output.llamaindex_docs
            )  # 📌 assessment_output consumed from stream is a dict hence attribute access might fail
            dynamic_metadata = input.assessment_output.dynamic_metadata
            prior_events = input.assessment_output.prior_events

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
            query_engine = await async_get_llamaindex_query_engine_from_docs(
                docs=llamaindex_docs, dynamic_metadata_by_clause_id=dynamic_metadata
            )

            # ---3. Llamaindex processing & LLM inference and analysis
            transaction = input.assessment_output.transaction
            structured_query = self._build_compliance_query(transaction)

            try:
                response = await query_engine.aquery(structured_query)
            except Exception as e:
                logger.error(f"LlamaIndex async query failed: {e}")
                decision = DecisionLevel.ND
                raw_response = f"LLM query failed due to: {str(e)}"
                response = None

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

            clause_hits = [
                doc.metadata["clause_id"]
                for doc in base_docs
                if "clause_id" in doc.metadata
            ]
            # 📌 Enrich LLM raw response with clause context for downstream traceability
            if clause_hits:
                clause_desc = (
                    f"\n\n🧠 Matched Clauses (from assessment agent's Neo4j+LangChain retrieval): "
                    + ", ".join(clause_hits)
                )
            else:
                clause_desc = "\n\n⚠️ No clause IDs matched in base documents."
            raw_response += clause_desc

            action_output = ActionOutput(
                action_id=f"action-{uuid.uuid4()}",
                decision=decision,
                raw_response=raw_response,
                source_nodes=source_nodes,
                context=input.context,
                clause_hits=clause_hits,  # clause_hits reff for downstream flow and agents i.e which clause matches with the txn via the langchain->llamaindexdocs i.e base_docs from the assessment agent
            )

            # ---3. Flag txn and notify UI as action agent action if decision is YES ---
            # 📌 here additional freeze txn or other autonomoous action cud be performed addition to pushing it to ui
            logger.info(
                f"[ActionAgent] Final decision: {decision} | Clause Hits: {clause_hits}"
            )

            if decision == DecisionLevel.YES:
                #  instead of relying on graph existence only check stream_id registry, decouple action forwarding from stream lifecycle
                if registry:
                    is_active = await registry.is_active(stream_id)
                    if not is_active:
                        logger.info(
                            f"[ActionAgent] Stream {stream_id} inactive — forwarding flagged txn anyway (post-abort)"
                        )
                else:
                    logger.warning(
                        f"[ActionAgent] Registry not found in context — forwarding anyway"
                    )
                    is_active = False
                await self._forward_flagged_txn(
                    action_output.to_dict(),
                    stream_id,
                    input.assessment_output.transaction,
                    is_active=is_active,
                )

            # ---4. Forward NO/ND to judge agent ---
            elif decision in [DecisionLevel.NO, DecisionLevel.ND]:
                await self._forward_to_judge(action_output)

            # ---5. Store MemoryEvent as needed both yes and no decisions (Phase 7) ---
            if decision in [DecisionLevel.YES, DecisionLevel.NO]:
                try:
                    prompt = structured_query
                    summary = await self.summarizer.async_summarize(prompt)
                    embedding = await asyncio.get_running_loop().run_in_executor(
                        None, self.embedding_model.embed_query, prompt
                    )
                    # build memory event
                    memory_event = MemoryEvent(
                        user_id=getattr(context, "user_id", None),
                        agent_name="action-agent",
                        prompt=prompt,
                        llm_response=raw_response,
                        decision=decision,  # Explicit field
                        original_transaction=transaction,  # Full original txn
                        relevant_clause_ids=clause_hits,
                        metadata={
                            "dynamic_metadata": dynamic_metadata,
                            "assessment_metadata": getattr(
                                input.assessment_output, "metadata", {}
                            ),
                            "score": getattr(input.assessment_output, "score", None),
                            "priority": getattr(
                                input.assessment_output, "priority", None
                            ),
                            "reasons": getattr(
                                input.assessment_output, "reasons", None
                            ),
                        },
                        extra_context={
                            "stream_id": stream_id,
                            "source_nodes": source_nodes,
                            "prior_events": prior_events,
                            "action_output_id": action_output.action_id,
                        },
                        summary=summary,
                        source="llm",  # set source="cache" when new txn matches to already existing memory events to skip inference and store the new txn as cached event in qdrant
                        llm_confidence=getattr(response, "confidence", None),
                        user_feedback=None,  # cud be set later after user review for ND type decisions forwarded from judge agent to the UI
                    )
                    # 🎈 when user reviews a decision in ui example ND or other events update event in qdrant
                    # updated_feedback = {"approved": True, "notes": "User confirmed this is a violation"}
                    # event.user_feedback = updated_feedback
                    # await memory_event_repository.update(event)  # You may need to implement an update method

                    logger.debug(
                        "📦 MemoryEvent payload (pre-store):\n%s",
                        json.dumps(memory_event.model_dump(), indent=2),
                    )
                    # Store asynchronously using the task registry to run as bg task
                    task_registry.add(
                        self.memory_event_repository.store(
                            memory_event,
                            embedding,
                        )
                    )
                    logger.info(
                        f"[MemoryEvent] Stored event for txn_id={transaction.get('txn_id')}, decision={decision}"
                    )
                except Exception as e:
                    logger.error(f"[MemoryEvent] Failed to store event: {e}")

        except Exception as e:
            logger.error(f"[ActionAgent] Failed in background LlamaIndex analysis: {e}")

        finally:
            # 📌 Decrement counter and emit final event if this was the last analysis for the stream along with resetting the same
            count = await analysis_counter_registry.decr(stream_id)
            if count == 0:
                await self._emit_final_post_abort_event(stream_id=stream_id)
                await analysis_counter_registry.reset(stream_id)

    async def _process_streamed_action(self, input: ActionInput, context: AgentContext):
        """
        This method should contain all the logic (steps 1-4) that is done in the default A2A path.
        """
        ao = input.assessment_output
        # 📌 supports both dict and object
        if isinstance(ao, dict):
            stream_id = ao.get("metadata", {}).get("stream_id", "NotDefined")
        else:
            stream_id = getattr(ao, "metadata", {}).get("stream_id", "NotDefined")
        # 📌 start analysis event send event to streaming-hub to display in ui
        await self._send_analysis_started_event(stream_id)
        # same  _handle_llamaindex_analysis call for each consumed event like a2a default flow
        await self._handle_llamaindex_analysis(input, context)

    async def start_action_agent_stream_worker(self):
        """
        NOTE- In "redistream" mode, you are viewing global compliance events as they happen,
        regardless of user or stream. For per-user or interactive tracing, switch to "default" mode.

        Start a background worker to consume from the assessed_events_stream and process each event.
        +-----------------------------+
        |     Per-Stream AgentGraph   |  (for direct, in-memory A2A)
        |   (Intake → Assessment)     |
        |        (stream_id: A)       |
        +-------------+---------------+
                    |
                    | (if assessment_type == "redistream")
                    v
        +---------------------------------------------------------------+
        |                  Redis Stream: assessed_events_stream         |
        |     [event: {stream_id: A, ...}]   [event: {stream_id: B, ...}]   ...   |
        +---------------------------------------------------------------+
                    |
                    | (global, stateless consumer)
                    v
        +---------------------------------------------------+
        |           ActionAgent Stream Worker(s)            |
        |  (Consumes events for ANY stream_id, processes    |
        |   each independently using included context)      |
        +---------------------------------------------------+
                    |
                    v
        +---------------------------------------------------+
        |      Downstream: UI, JudgeAgent, etc.             |
        |  (Events/results tagged with stream_id)           |
        +---------------------------------------------------+

        """
        redis_streams = RedisStreams()
        async for msg_id, data in assessed_events_consumer_worker(
            redis_streams=redis_streams
        ):
            output_dict = data.get("output", {})
            context_dict = data.get("context", {})
            stream_id = (output_dict.get("metadata", {}) or {}).get(
                "stream_id", "NotDefined"
            )

            logger.info(
                f"[Worker] Received message from assessed_events_stream: msg_id={msg_id}, stream_id={stream_id}"
            )
            try:
                # 📌 reconstruct assessment output from consume redistream dict fo downstream consistency
                assessment_output = AssessmentOutput(**output_dict)
                # Reconstruct ActionInput and AgentContext
                action_input = ActionInput(
                    assessment_output=assessment_output, context=context_dict
                )
                context = AgentContext(**context_dict)
                await self._process_streamed_action(action_input, context)
                await redis_streams.ack(
                    "assessed_events_stream", "action_agents", msg_id
                )
                logger.info(
                    f"[Worker] Successfully processed and acked msg_id={msg_id}, stream_id={stream_id}"
                )
            except Exception as e:
                logger.error(
                    f"[Worker] Error processing msg_id={msg_id}, stream_id={stream_id}: {e}",
                    exc_info=True,
                )
                # Optionally: push to DLQ or take other recovery action here
        await redis_streams.close()

    @jsonrpc_method
    async def invoke(self, input: ActionInput, context: AgentContext) -> ActionOutput:

        config = context.config or StreamingConfig()
        if isinstance(config, dict):
            assessment_type = config.get("assessment_type", "default")
        else:
            assessment_type = config.assessment_type or "default"

        # 📌 CASE: default a2a message passed from assessment agent
        logger.info(
            f"[ActionAgent] Recieve assessment : {input.assessment_output.assessment_id}"
        )

        stream_id = input.assessment_output.metadata.get("stream_id", "NotDefined")

        # 📌 Increment analysis count for this stream
        await analysis_counter_registry.incr(stream_id)

        # 📌 fire and forget run the analysis in bg task coroutine and if YES then push to streaming hub else to judge agent
        asyncio.create_task(self._handle_llamaindex_analysis(input, context))

        # 📌 immediate return statement for compliance analysis initiated + send event to streaming-hub to display in ui
        await self._send_analysis_started_event(stream_id)
        return ActionOutput(
            action_id=f"action-{uuid.uuid4()}",
            decision=DecisionLevel.ND,
            raw_response="Compliance analysis is in progress",
            source_nodes=[],
            context=input.context,
            clause_hits=[],
        )

    async def _send_analysis_started_event(self, stream_id: str):
        """
        Notify UI via streaming hub that compliance analysis is in progress
        """
        event = {
            "event": "3️⃣[ActionAgent]",
            "message": "🔍 Compliance analysis in progress...",
            "stream_id": stream_id,
            "flagged": False,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "agent": "action-agent",
            "level": "info",
        }
        success = await forward_event_to_streaming_hub(event)
        if not success:
            logger.warning(
                f"[NotifyStart]❌ Could not notify UI that analysis started and  was sent to DLQ:. Stream ID: {stream_id}"
            )

    async def _forward_flagged_txn(
        self, data: dict, stream_id: str, txn: dict, is_active: bool
    ):
        """
        Forward flagged txn to streaming hub for UI alert
        """
        # attach txn inside data
        data_with_txn = {
            **data,
            "txn": txn,  # 📌 original txn data for tracebility/searching in ui for future by sender/reciever
        }
        event = {
            "event": "3️⃣[ActionAgent]",
            "message": f"🚨 Action Taken: {data['decision']}",
            "stream_id": stream_id,
            "data": data_with_txn,
            "flagged": True,  # the streaming-hub event dto shud be sync with optional flagged key
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "agent": "action-agent",  # to filter in UI
            "level": "warn",
            "post_abort": not is_active,
        }
        success = await forward_event_to_streaming_hub(event)
        if not success:
            logger.warning(
                f"[ForwardWithFallback]❌ Event failed to forward and was sent to DLQ: stream_id={stream_id}"
            )

    async def _forward_to_judge(self, output: ActionOutput):
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
