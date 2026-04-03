from pydantic import BaseModel
from typing import List, Any

class WorkspaceCreate(BaseModel):
    db_url: str

class WorkspaceUpdate(BaseModel):
    db_url: str

class DashboardUpdate(BaseModel):
    dashboard: List[Any]
