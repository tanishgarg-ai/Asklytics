from pydantic import BaseModel

class ShareLinkCreate(BaseModel):
    role: str
    expires_in_hours: int = 24
