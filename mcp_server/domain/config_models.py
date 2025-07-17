"""
mcp_server/domain/config_models.py
"""

from enum import Enum
from pydantic import BaseModel
from typing import List, Optional


class PriorityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class StreamingConfig(BaseModel):
    priority: Optional[List[PriorityLevel]] = [
        "HIGH"
    ]  # high means only the high priority transactions will be passed forward to the action agent from assessment agent for autonomous actions without human intervention
    source_filters: Optional[List[str]] = (
        None  # ["faker","bank_1","api_custom_bank_2"] for single or multiple source selection in electron client by end user admin
    )
    assessment_type: Optional[str] = None
    caching: bool = False  # enable-disables memory cache short circuiting
