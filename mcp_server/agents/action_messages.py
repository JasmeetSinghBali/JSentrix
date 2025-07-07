"""
mcp_server/agents/action_messages.py
"""

from .message_a2aserializer import A2AMessageSerializable
from .base_agent import AgentContext
from typing import Optional, Union, Dict, Any, List
from datetime import datetime, timezone
from .assessment_messages import AssessmentOutput
from enum import Enum


class ActionInput(A2AMessageSerializable):
    """
    Wraps output from AssessmentAgent, forwards to JudgeAgent or executes direct action.

    A2A compliant input for action agent is the output from assessment agent:
    - assessment_ouptut- llamaindex docs, dynamic metadata...
    - common context from upstream intake->assessment agents or if not passed then defaults to AgentContext in reff to action_agent
    """

    def __init__(
        self,
        assessment_output: AssessmentOutput,
        context: Optional[AgentContext] = None,
    ):
        self.assessment_output = assessment_output
        self.context = context or AgentContext(
            request_id="system",
            user_id="action_agent",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


class DecisionLevel(str, Enum):
    ND = "ND"
    YES = "YES"
    NO = "NO"


class ActionOutput(A2AMessageSerializable):
    """
    A2A compliant output for action agent for downstream judge agent
    NOTE- Action agent only passes those txn's to the judge agent that are not conclusive i.e marked as "ND" or "NO"
      the llm is not able to infer wheather they voilate or the llm has inferred that it does not not voilates the clauses

    includes:
    - final decision/inference
    - raw model output
    - Source nodes for clause tracing
    - Metadata for reranking/judging

    example:
        {
            "action_id": "action-12345",
            "decision": "YES",
            "raw_response": "YES, this transaction violates Clause C1 and C4 due to ...",
            "source_nodes": [
                {
                "metadata": {
                    "clause_id": "C1",
                    "summary": "Customer failed to provide KYC within 30 days",
                    "score": 0.91,
                    "decayed_score": 0.83,
                    "hybrid_score": 0.79
                }
                },
                {
                "metadata": {
                    "clause_id": "C4",
                    "summary": "AML threshold breached",
                    "score": 0.87,
                    "decayed_score": 0.81,
                    "hybrid_score": 0.77
                }
                }
            ],
            # 📌 NOTE- here context if passed from intake -> assessment then it will have that strucutre if not then new context in reff to action agent will be passed to downstream judge agent
            "context": {
                "request_id": "txn-8970",
                "user_id": "action_agent",
                "timestamp": "2025-06-26T07:03:21.311Z"
            }
        }
    """

    def __init__(
        self,
        action_id: str,
        decision: DecisionLevel,  # "ND" OR "YES" OR "NO" where nd is non-deterministic
        raw_response: Union[str, Dict[str, Any]],
        context: Optional[AgentContext] = None,
        source_nodes: Optional[List[Dict[str, Any]]] = None,
        clause_hits: Optional[List[str]] = None,  # e.g., ["C002", "C007"]
    ):
        self.action_id = (
            action_id  # usage: ActionOutput(action_id=f"action-{uuid.uuid4()}",)
        )
        self.decision = decision
        self.raw_response = raw_response
        self.context = context or AgentContext(
            request_id="system",
            user_id="action_agent",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.source_nodes = source_nodes or []
        self.clause_hits = clause_hits or []
