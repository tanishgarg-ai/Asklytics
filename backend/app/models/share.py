from pydantic import BaseModel

class ShareLinkCreate(BaseModel):
    """
    Pydantic schema for creating a new workspace share link.
    """
    role: str
    expires_in_hours: int = 24
