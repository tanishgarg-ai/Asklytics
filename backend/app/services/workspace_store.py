import json
import uuid
import jwt
import os
from datetime import datetime, timedelta, timezone
from app.db import SessionLocal, Workspace, ShareLink
from app.services.crypto import encrypt


def get_secret_key():
    return os.getenv("SECRET_KEY", "fallback_secret_key_for_dev")


def create_workspace(db_url: str) -> Workspace:
    db = SessionLocal()
    try:
        workspace_id = str(uuid.uuid4())
        encrypted_url = encrypt(db_url)
        new_workspace = Workspace(
            workspace_id=workspace_id,
            encrypted_db_url=encrypted_url,
            dashboard_state="[]",
            chat_history="[]",
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_workspace)
        db.commit()
        db.refresh(new_workspace)
        return new_workspace
    finally:
        db.close()


def get_workspace(workspace_id: str) -> Workspace:
    db = SessionLocal()
    try:
        return db.query(Workspace).filter(Workspace.workspace_id == workspace_id).first()
    finally:
        db.close()


def update_dashboard(workspace_id: str, charts: list[dict]):
    db = SessionLocal()
    try:
        workspace = db.query(Workspace).filter(Workspace.workspace_id == workspace_id).first()
        if workspace:
            workspace.dashboard_state = json.dumps(charts)
            db.commit()
    finally:
        db.close()


def append_chat_message(workspace_id: str, role: str, content: str):
    db = SessionLocal()
    try:
        workspace = db.query(Workspace).filter(Workspace.workspace_id == workspace_id).first()
        if workspace:
            history = json.loads(workspace.chat_history)
            history.append({"role": role, "content": content})
            workspace.chat_history = json.dumps(history)
            db.commit()
    finally:
        db.close()


def create_share_link(workspace_id: str, role: str, expires_in_hours: int) -> str:
    db = SessionLocal()
    try:
        token_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        new_link = ShareLink(
            token_id=token_id,
            workspace_id=workspace_id,
            role=role,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at
        )
        db.add(new_link)
        db.commit()

        payload = {
            "workspace_id": workspace_id,
            "role": role,
            "token_id": token_id,
            "exp": int(expires_at.timestamp())
        }
        token = jwt.encode(payload, get_secret_key(), algorithm="HS256")
        return token
    finally:
        db.close()


def validate_share_token(token: str) -> tuple[str, str]:
    db = SessionLocal()
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=["HS256"])
        workspace_id = payload.get("workspace_id")
        role = payload.get("role")
        token_id = payload.get("token_id")

        link = db.query(ShareLink).filter(ShareLink.token_id == token_id).first()
        if not link:
            raise ValueError("Token revoked or invalid")

        return workspace_id, role
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
        raise ValueError("Invalid token")
    finally:
        db.close()

def clear_workspace_state(workspace_id: str):
    db = SessionLocal()
    try:
        workspace = db.query(Workspace).filter(Workspace.workspace_id == workspace_id).first()
        if workspace:
            workspace.dashboard_state = "[]"
            workspace.chat_history = "[]"
            db.commit()
    finally:
        db.close()
