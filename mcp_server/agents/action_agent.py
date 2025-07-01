"""
mcp_server/agents/action_agent.py
"""

from .base_agent import BaseAgent, JsonRpcAgentMixin, AgentContext, jsonrpc_method
from .action_messages import ActionInput, ActionOuput
from utils.logger import get_logger
from application.retrievers.llamaindex_retriever import (
    async_get_llamaindex_query_engine_from_docs,
)

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
            pass
        else:  # default a2a message passed from assessment agent
            # ---1. Prepare LlamaIndex query engine ---
            llamaindex_docs = input.assessment_output.llamaindex_docs
            dynamic_metadata = input.assessment_output.dynamic_metadata

            query_engine = async_get_llamaindex_query_engine_from_docs(
                docs=llamaindex_docs, dynamic_metadata_by_clause_id=dynamic_metadata
            )

            logger.info(
                f"[ActionAgent] Recieves assessment: {input.assessment_output.assessment_id}"
            )
