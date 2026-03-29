from pydantic import BaseModel

class WorkspaceCreate(BaseModel):
    db_url: str

class WorkspaceUpdate(BaseModel):
    db_url: str
