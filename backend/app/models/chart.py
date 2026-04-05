from pydantic import BaseModel

class ChatRequest(BaseModel):
    """
    Pydantic schema for inbound natural language queries.
    """
    query: str
