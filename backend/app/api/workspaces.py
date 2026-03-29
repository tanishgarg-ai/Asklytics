import json
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import Optional
from app.models.workspace import WorkspaceCreate, WorkspaceUpdate
from app.models.share import ShareLinkCreate
from app.models.chart import ChatRequest
from app.services.workspace_store import (
    create_workspace, get_workspace, update_dashboard,
    append_chat_message, create_share_link, validate_share_token
)
from app.services.ingestor import ingest_from_sql_source
from app.services.data_engine import get_schema
from app.services.agent.graph import agent_executor

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


def get_role(workspace_id: str, x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
             token: Optional[str] = Query(None)):
    if token:
        try:
            tok_ws_id, role = validate_share_token(token)
            if tok_ws_id != workspace_id:
                raise HTTPException(status_code=403, detail="Token does not match workspace")
            return role
        except Exception as e:
            raise HTTPException(status_code=403, detail=str(e))
    elif x_workspace_id == workspace_id:
        return "owner"
    else:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.post("")
def create_new_workspace(req: WorkspaceCreate):
    workspace = create_workspace(req.db_url)
    ws_id = workspace.workspace_id

    try:
        tables, schema = ingest_from_sql_source(ws_id, req.db_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect and ingest DB: {e}")

    initial_state = {
        "workspace_id": ws_id,
        "is_dashboard_init": True,
        "retry_count": 0
    }
    result = agent_executor.invoke(initial_state)

    if result.get("execution_error"):
        raise HTTPException(status_code=500, detail=f"LLM Generation failed: {result['execution_error']}")

    payloads = result.get("plotly_json_payload", [])
    update_dashboard(ws_id, payloads)

    return {
        "workspace_id": ws_id,
        "schema": schema,
        "dashboard": payloads
    }


@router.get("/{workspace_id}")
def load_workspace(workspace_id: str, x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
                   token: Optional[str] = None):
    role = get_role(workspace_id, x_workspace_id, token)
    workspace = get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    schema = get_schema(workspace_id)
    return {
        "schema": schema,
        "dashboard": json.loads(workspace.dashboard_state),
        "chat_history": json.loads(workspace.chat_history),
        "role": role
    }


@router.post("/{workspace_id}/chat")
def chat_generate(workspace_id: str, req: ChatRequest,
                  x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"), token: Optional[str] = None):
    role = get_role(workspace_id, x_workspace_id, token)
    if role not in ["owner", "edit"]:
        raise HTTPException(status_code=403, detail="Upgrade to edit access to interact.")

    workspace = get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    append_chat_message(workspace_id, "user", req.query)

    initial_state = {
        "workspace_id": workspace_id,
        "user_query": req.query,
        "is_dashboard_init": False,
        "retry_count": 0
    }
    result = agent_executor.invoke(initial_state)

    if result.get("execution_error"):
        error_msg = result['execution_error']
        append_chat_message(workspace_id, "assistant", f"Sorry, I encountered an error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

    payload = result.get("plotly_json_payload", {})
    sql_used = result.get("generated_sql", "")

    current_charts = json.loads(workspace.dashboard_state)
    current_charts.append(payload)
    update_dashboard(workspace_id, current_charts)

    append_chat_message(workspace_id, "assistant",
                        f"I've added the chart to your dashboard. Query used:\n```sql\n{sql_used}\n```")

    return {
        "plotly_payload": payload,
        "sql_used": sql_used,
        "chat_history": json.loads(get_workspace(workspace_id).chat_history)
    }


@router.post("/{workspace_id}/share")
def get_share_link(workspace_id: str, req: ShareLinkCreate,
                   x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID")):
    role = get_role(workspace_id, x_workspace_id, None)
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can easily share")

    token = create_share_link(workspace_id, req.role, req.expires_in_hours)
    return {
        "share_url": f"https://asklytics.app/w/{workspace_id}?token={token}"
    }


@router.put("/{workspace_id}/settings")
def update_settings(workspace_id: str, req: WorkspaceUpdate,
                    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID")):
    role = get_role(workspace_id, x_workspace_id, None)
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can update settings")

    workspace = get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        tables, schema = ingest_from_sql_source(workspace_id, req.db_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect and ingest DB: {e}")

    from app.services.crypto import encrypt
    from app.db import SessionLocal
    db = SessionLocal()
    ws = db.query(type(workspace)).filter_by(workspace_id=workspace_id).first()
    ws.encrypted_db_url = encrypt(req.db_url)
    db.commit()
    db.close()

    initial_state = {
        "workspace_id": workspace_id,
        "is_dashboard_init": True,
        "retry_count": 0
    }
    result = agent_executor.invoke(initial_state)

    if result.get("execution_error"):
        raise HTTPException(status_code=500, detail=f"LLM generated an error regenerating: {result['execution_error']}")

    payloads = result.get("plotly_json_payload", [])
    update_dashboard(workspace_id, payloads)

    return {
        "workspace": {
            "schema": schema,
            "dashboard": payloads,
            "chat_history": json.loads(get_workspace(workspace_id).chat_history),
            "role": "owner"
        }
    }
