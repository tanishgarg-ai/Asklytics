import json
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import Optional
from app.models.workspace import WorkspaceCreate, WorkspaceUpdate, DashboardUpdate
from app.models.share import ShareLinkCreate
from app.models.chart import ChatRequest
from app.services.workspace_store import (
    create_workspace, get_workspace, update_dashboard,
    append_chat_message, create_share_link, validate_share_token
)
from app.services.ingestor import ingest_from_sql_source
from app.services.data_engine import get_schema, execute_and_format_chart
from app.services.agent.graph import agent_executor

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


def get_role(workspace_id: str, x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
             token: Optional[str] = Query(None)):
    """
    Resolves and validates the user's role for a specific workspace.

    Args:
        workspace_id (str): The workspace to check access for.
        x_workspace_id (Optional[str]): The workspace owner ID header.
        token (Optional[str]): A JWT share token, if accessing via a shared link.

    Returns:
        str: The computed role (e.g., 'owner', 'edit', 'viewer').

    Raises:
        HTTPException: If authorization fails or the token is invalid.
    """
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
    """
    Creates a new workspace, ingests the provided database, and generates an initial dashboard.

    Args:
        req (WorkspaceCreate): Expected payload containing the database connection URL.

    Returns:
        dict: Initialization response with workspace_id, schema, dashboard state, and narration steps.
    """
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
        "dashboard": payloads,
        "chat_history": [],
        "narration_steps": result.get("narration_steps", [])
    }


@router.get("/{workspace_id}")
def load_workspace(workspace_id: str, x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
                   token: Optional[str] = None):
    """
    Loads an existing workspace's schema, dashboard layout, and chat history.

    Args:
        workspace_id (str): The workspace identifier.
        x_workspace_id (Optional[str]): The workspace owner ID header.
        token (Optional[str]): Optional share token for guest access.

    Returns:
        dict: The workspace state elements.
    """
    role = get_role(workspace_id, x_workspace_id, token)
    workspace = get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    schema = get_schema(workspace_id)
    return {
        "schema": schema,
        "dashboard": json.loads(workspace.dashboard_state, parse_constant=lambda c: None),
        "chat_history": json.loads(workspace.chat_history, parse_constant=lambda c: None),
        "role": role
    }


@router.post("/{workspace_id}/charts/{chart_index}/narrate")
def narrate_chart_endpoint(workspace_id: str, chart_index: int,
                  x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"), token: Optional[str] = None):
    role = get_role(workspace_id, x_workspace_id, token)
    if role not in ["owner", "edit"]:
        raise HTTPException(status_code=403, detail="Upgrade to edit access to interact.")

    workspace = get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    current_charts = json.loads(workspace.dashboard_state, parse_constant=lambda c: None)
    if chart_index < 0 or chart_index >= len(current_charts):
        raise HTTPException(status_code=404, detail="Chart not found")

    from app.services.agent.nodes import narration_generator
    
    chart_title = current_charts[chart_index].get('layout', {}).get('title', {}).get('text', '')
    
    fake_state = {
        "workspace_id": workspace_id,
        "user_query": f"Please provide an analytical overview of this chart and its significant data points. Context: {chart_title}",
        "agent_intent": "explain_existing",
        "target_chart_index": chart_index,
        "existing_dashboard": current_charts
    }
    
    result = narration_generator(fake_state)
    steps = result.get("narration_steps", [])
    
    # Cache it in the db automatically
    if steps:
        current_charts[chart_index]["_narration_steps"] = steps
        update_dashboard(workspace_id, current_charts)

    return {
        "narration_steps": steps
    }


@router.post("/{workspace_id}/chat")
def chat_generate(workspace_id: str, req: ChatRequest,
                  x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"), token: Optional[str] = None):
    """
    Handles a user's natural language chart request against their workspace.

    Depending on the query intent, this uses LLM agents to either generate a new chart
    via SQL, answer a follow-up question, or narrate an existing chart.

    Args:
        workspace_id (str): The workspace identifier.
        req (ChatRequest): The payload containing the user's natural language query.
        x_workspace_id (Optional[str]): Header for owner validation.
        token (Optional[str]): Optional share token granting edit access.

    Returns:
        dict: The updated chat history, the generated plotly payload (if new), and narration.
    """
    role = get_role(workspace_id, x_workspace_id, token)
    if role not in ["owner", "edit"]:
        raise HTTPException(status_code=403, detail="Upgrade to edit access to interact.")

    workspace = get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    append_chat_message(workspace_id, "user", req.query)

    current_charts = json.loads(workspace.dashboard_state, parse_constant=lambda c: None)

    initial_state = {
        "workspace_id": workspace_id,
        "user_query": req.query,
        "is_dashboard_init": False,
        "retry_count": 0,
        "existing_dashboard": req.existing_dashboard
    }
    result = agent_executor.invoke(initial_state)

    if result.get("execution_error"):
        error_msg = result['execution_error']
        append_chat_message(workspace_id, "assistant", f"Sorry, I encountered an error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

    agent_intent = result.get("agent_intent", "generate_new")
    narration_steps = result.get("narration_steps", [])
    target_chart_index = result.get("target_chart_index")
    agent_msg = result.get("agent_message", "")

    resp = {
        "agent_intent": agent_intent,
        "narration_steps": narration_steps,
        "plotly_payload": None,
        "sql_used": "",
        "target_chart_index": target_chart_index,
        "agent_message": agent_msg,
        "chat_history": []
    }

    if agent_intent == "follow_up":
        append_chat_message(workspace_id, "assistant", agent_msg or "Can you provide more details?")
    elif agent_intent == "explain_existing":
        if target_chart_index is not None and target_chart_index < len(current_charts):
            current_charts[target_chart_index]["_narration_steps"] = narration_steps
            update_dashboard(workspace_id, current_charts)
            action = {"type": "narrate", "index": target_chart_index}
        else:
            action = None
        append_chat_message(workspace_id, "assistant", agent_msg or "I can explain that using an existing chart on the dashboard.", action=action)
    else:
        payload = result.get("plotly_json_payload", {})
        sql_used = result.get("generated_sql", "")
        
        current_charts.append(payload)
        update_dashboard(workspace_id, current_charts)

        append_chat_message(workspace_id, "assistant",
                            f"I've added the chart to your dashboard. Query used:\n```sql\n{sql_used}\n```")

        resp["plotly_payload"] = payload
        resp["sql_used"] = sql_used

    resp["chat_history"] = json.loads(get_workspace(workspace_id).chat_history, parse_constant=lambda c: None)
    return resp


@router.post("/{workspace_id}/share")
def get_share_link(workspace_id: str, req: ShareLinkCreate,
                   x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID")):
    """
    Creates a secure, timed share link for a workspace.

    Args:
        workspace_id (str): The workspace identifier.
        req (ShareLinkCreate): The payload specifying the role and expiration hours.
        x_workspace_id (Optional[str]): Verification marker showing owner privileges.

    Returns:
        dict: An object containing the built share_url.
    """
    role = get_role(workspace_id, x_workspace_id, None)
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can easily share")

    token = create_share_link(workspace_id, req.role, req.expires_in_hours)
    return {
        "share_url": f"https://asklytics.app/w/{workspace_id}?token={token}"
    }


@router.post("/{workspace_id}/refresh")
def refresh_dashboard_data(workspace_id: str, x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID")):
    """
    Refreshes the data for all charts on a dashboard by re-running their underlying SQL against DuckDB.

    Args:
        workspace_id (str): The workspace identifier.
        x_workspace_id (Optional[str]): Verification marker.

    Returns:
        dict: A success status alongside the newly populated dashboard payloads.
    """
    role = get_role(workspace_id, x_workspace_id, None)
    if role not in ["owner", "edit"]:
        raise HTTPException(status_code=403, detail="Not authorized to refresh data")

    workspace = get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    from app.services.crypto import decrypt
    from app.services.ingestor import ingest_from_sql_source
    
    db_url = decrypt(workspace.encrypted_db_url)
    try:
        tables, schema = ingest_from_sql_source(workspace_id, db_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to gracefully sync database: {e}")

    current_dashboard = json.loads(workspace.dashboard_state, parse_constant=lambda c: None)
    chat_history = json.loads(workspace.chat_history, parse_constant=lambda c: None)
    payloads = []
    
    for i, chart in enumerate(current_dashboard):
        sql = chart.get("_sql")
        meta = chart.get("_meta")
        if sql and meta:
            try:
                new_payload = execute_and_format_chart(workspace_id, sql, meta)
                
                # Check if data shifted
                data_changed = json.dumps(chart.get("data", []), sort_keys=True) != json.dumps(new_payload.get("data", []), sort_keys=True)
                
                if "grid_layout" in chart:
                    new_payload["grid_layout"] = chart["grid_layout"]
                    
                if "_narration_steps" in chart and not data_changed:
                    new_payload["_narration_steps"] = chart.get("_narration_steps")
                    
                # Defuse old chat buttons if data shifted
                if data_changed:
                    for msg in chat_history:
                        action = msg.get("action")
                        if action and action.get("type") == "narrate" and action.get("index") == i:
                            msg["action"]["type"] = "narrate_expired"
                            
                if "layout" in chart:
                    new_payload["layout"].update(chart.get("layout", {}))
                payloads.append(new_payload)
            except Exception:
                payloads.append(chart)
        else:
            payloads.append(chart)

    update_dashboard(workspace_id, payloads)
    
    from app.db import SessionLocal
    db = SessionLocal()
    ws = db.query(type(workspace)).filter_by(workspace_id=workspace_id).first()
    if ws:
        ws.chat_history = json.dumps(chat_history)
        db.commit()
    db.close()

    return {
        "status": "success",
        "dashboard": payloads,
        "chat_history": chat_history,
        "schema": schema
    }


@router.put("/{workspace_id}/dashboard")
def update_dashboard_layout(workspace_id: str, req: DashboardUpdate,
                            x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
                            token: Optional[str] = None):
    """
    Saves a modified arrangement, grid layout, or deletion of charts on the dashboard.

    Args:
        workspace_id (str): The workspace identifier.
        req (DashboardUpdate): The payload representing the updated list of chart configurations.
        x_workspace_id (Optional[str]): Owner marker.
        token (Optional[str]): Token mapped to a role (must have >viewer access to edit).

    Returns:
        dict: A success status wrapper.
    """
    role = get_role(workspace_id, x_workspace_id, token)
    if role not in ["owner", "edit"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit dashboard")
    
    workspace = get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    update_dashboard(workspace_id, req.dashboard)
    
    return {"status": "success"}


@router.put("/{workspace_id}/settings")
def update_settings(workspace_id: str, req: WorkspaceUpdate,
                    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID")):
    """
    Updates global workspace settings, primarily focused on modifying the underlying db_url.
    This triggers a re-ingestion of the new DB and automatically attempts to refresh existing charts.

    Args:
        workspace_id (str): The workspace identifier.
        req (WorkspaceUpdate): The payload containing the new db_url.
        x_workspace_id (Optional[str]): Owner verification marker.

    Returns:
        dict: The newly re-evaluated workspace schema and dashboard state.
    """
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

    current_dashboard = json.loads(workspace.dashboard_state, parse_constant=lambda c: None)
    chat_history = json.loads(workspace.chat_history, parse_constant=lambda c: None)
    payloads = []
    
    for i, chart in enumerate(current_dashboard):
        sql = chart.get("_sql")
        meta = chart.get("_meta")
        if sql and meta:
            try:
                new_payload = execute_and_format_chart(workspace_id, sql, meta)
                
                data_changed = json.dumps(chart.get("data", []), sort_keys=True) != json.dumps(new_payload.get("data", []), sort_keys=True)
                
                if "grid_layout" in chart:
                    new_payload["grid_layout"] = chart["grid_layout"]
                if "_narration_steps" in chart and not data_changed:
                    new_payload["_narration_steps"] = chart.get("_narration_steps")
                
                if data_changed:
                    for msg in chat_history:
                        action = msg.get("action")
                        if action and action.get("type") == "narrate" and action.get("index") == i:
                            msg["action"]["type"] = "narrate_expired"
                            
                if "layout" in chart:
                    new_payload["layout"].update(chart.get("layout", {}))
                
                payloads.append(new_payload)
            except Exception:
                payloads.append(chart)
        else:
            payloads.append(chart)
            
    update_dashboard(workspace_id, payloads)
    
    db = SessionLocal()
    ws = db.query(type(workspace)).filter_by(workspace_id=workspace_id).first()
    if ws:
        ws.chat_history = json.dumps(chat_history)
        db.commit()
    db.close()

    return {
        "workspace": {
            "schema": schema,
            "dashboard": payloads,
            "chat_history": chat_history,
            "role": "owner"
        }
    }
