from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    """
    Pydantic schema for inbound natural language queries.
    """
    query: str
    existing_dashboard: Optional[List[dict]] = []
