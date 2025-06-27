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
    priority: Optional[List[PriorityLevel]] = ["HIGH"]
    source_filters: Optional[List[str]] = (
        None  # ["faker","bank_1","api_custom_bank_2"] for single or multiple source selection in electron client by end user admin
    )
    assessment_type: Optional[str] = None
