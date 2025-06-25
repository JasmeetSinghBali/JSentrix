"""
mcp_server/agents/agent_graph.py

AgentGraph: Composes a dedicated per-stream agent pipeline.

Each stream_id gets an isolated Intake → Assessment → Action agent flow,
enabling per-client control, scaling, and state encapsulation
"""

from agents.intake_agent import IntakeAgent
from agents.assessment_agent import AssessmentAgent

# from agents.action_agent import ActionAgent


class AgentGraph:
    def __init__(self, stream_id: str):
        """
        Create a new agent graph (intake → assess → action) for this stream.
        """
        self.stream_id = stream_id
        # self.action_agent = ActionAgent(stream_id=stream_id)
        # 🎈 uncomment below action_agent injection once ActionAgent is setup
        # self.assessment_agent = AssessmentAgent(action_agent=self.action_agent)
        self.assessment_agent = AssessmentAgent()
        self.intake_agent = IntakeAgent(assessment_agent=self.assessment_agent)

    def get_intake(self) -> IntakeAgent:
        return self.intake_agent

    def get_assessment(self) -> AssessmentAgent:
        return self.assessment_agent

    # def get_action(self) -> ActionAgent:
    #     return self.action_agent
