"""
mcp_server/infrastructure/agent_graphs_store.py

# agent_graphs: in-memory map is needed as object memory stream_id -> AgentGraph
# AgentGraph holds actual agent instances
# (e.g., IntakeAgent, AssessmentAgent, ActionAgent) and
# potentially state (like in-memory buffers or coroutines). Redis cannot serialize this.
"""

from typing import Dict
from agents.agent_graph import AgentGraph

# In-memory agent graph store
agent_graphs: Dict[str, AgentGraph] = {}
