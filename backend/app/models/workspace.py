from pydantic import BaseModel
from typing import List, Any

class WorkspaceCreate(BaseModel):
    """Pydantic schema representing the initial creation payload of a workspace."""
    db_url: str

class WorkspaceUpdate(BaseModel):
    """Pydantic schema for updating core workspace settings."""
    db_url: str

class DashboardUpdate(BaseModel):
    """Pydantic schema for bulk updating the chart configuration layout of a dashboard."""
    dashboard: List[Any]
