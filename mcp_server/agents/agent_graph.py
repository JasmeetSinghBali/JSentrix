"""
mcp_server/agents/agent_graph.py

AgentGraph: Composes a dedicated per-stream agent pipeline.

Each stream_id gets an isolated Intake → Assessment → Action → Judge agent flow,
enabling per-client control, scaling, and state encapsulation
"""

from .base_agent import AgentContext
from agents.intake_agent import IntakeAgent
from agents.assessment_agent import AssessmentAgent
from agents.action_agent import ActionAgent

# from agents.judge_agent import JudgeAgent


class AgentGraph:
    def __init__(self, stream_id: str):
        """
        Create a new agent graph (intake → assess → action → judge agent) for this stream
        instantiated in reverse order judge-action-assess-intake
        """
        self.stream_id = stream_id

        # 🎈 uncomment below judge_agent injection once judge agent is setup
        # self.judge_agent = JudgeAgent()
        # self.action_agent = ActionAgent(judge_agent=self.judge_agent)
        self.action_agent = ActionAgent()
        self.assessment_agent = AssessmentAgent(action_agent=self.action_agent)
        self.intake_agent = IntakeAgent(assessment_agent=self.assessment_agent)

    def get_intake(self) -> IntakeAgent:
        return self.intake_agent

    def get_assessment(self) -> AssessmentAgent:
        return self.assessment_agent

    def get_action(self) -> ActionAgent:
        return self.action_agent

    # def get_judge(self) -> JudgeAgent:
    #     return self.judge_agent

    async def abort(self, stream_id: str, context: AgentContext):
        if hasattr(self, "intake_agent"):
            await self.intake_agent.abort({"stream_id": stream_id}, context)
        # 📌 If adding assessment → action → other agents later that have stream abort support then:
        # await self.assessment_agent.abort(...) if hasattr(self, "assessment_agent")
