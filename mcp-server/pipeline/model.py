from typing import List, Optional
from pydantic import BaseModel

class ClauseMetaData(BaseModel):
    category: Optional[str]
    section_header: Optional[str]
    references: List[str]
    amends: List[str]
    overrides: List[str]
    source: str

class Clause(BaseModel):
    id: str
    title: Optional[str]
    text: str
    metadata: ClauseMetaData