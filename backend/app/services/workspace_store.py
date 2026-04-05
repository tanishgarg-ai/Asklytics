import json
import uuid
import jwt
import os
from datetime import datetime, timedelta, timezone
from app.db import SessionLocal, Workspace, ShareLink
from app.services.crypto import encrypt


def get_secret_key():
    """
    Retrieves the secret key used for JWT signing from the environment.

    Returns:
        str: The secret key string.
    """
    return os.getenv("SECRET_KEY", "fallback_secret_key_for_dev")


def create_workspace(db_url: str) -> Workspace:
    """
    Creates a new Workspace record in the database with an encrypted database URL.

    Args:
        db_url (str): The raw plaintext database connection URL to encrypt and save.

    Returns:
        Workspace: The newly created Workspace ORM object.
    """
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
    """
    Retrieves a Workspace record by its unique identifier.

    Args:
        workspace_id (str): The unique identifier.

    Returns:
        Workspace: The ORM object if found, otherwise None.
    """
    db = SessionLocal()
    try:
        return db.query(Workspace).filter(Workspace.workspace_id == workspace_id).first()
    finally:
        db.close()


def update_dashboard(workspace_id: str, charts: list[dict]):
    """
    Persists the updated dashboard state (list of charts) for a workspace.

    Args:
        workspace_id (str): The unique identifier.
        charts (list[dict]): A list of Plotly chart JSON payloads.
    """
    db = SessionLocal()
    try:
        workspace = db.query(Workspace).filter(Workspace.workspace_id == workspace_id).first()
        if workspace:
            workspace.dashboard_state = json.dumps(charts)
            db.commit()
    finally:
        db.close()


def append_chat_message(workspace_id: str, role: str, content: str):
    """
    Appends a new message to the persistent chat history of the workspace.

    Args:
        workspace_id (str): The workspace identifier.
        role (str): The role ('user' or 'assistant').
        content (str): The text content of the message.
    """
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
    """
    Generates and saves a shareable link token granting specified access.

    Args:
        workspace_id (str): The workspace identifier.
        role (str): The role/permission to grant ('viewer', 'edit', etc.).
        expires_in_hours (int): The duration until token expiration in hours.

    Returns:
        str: A signed JWT representing the share link.
    """
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
    """
    Validates a share token and extracts the corresponding workspace ID and role.

    Args:
        token (str): The JWT share token to validate.

    Returns:
        tuple[str, str]: A tuple containing the workspace ID and the assigned role.

    Raises:
        ValueError: If the token is invalid, expired, or revoked.
    """
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
    """
    Resets the workspace dashboard configuration and chat history back to empty arrays.

    Args:
        workspace_id (str): The workspace to clear.
    """
    db = SessionLocal()
    try:
        workspace = db.query(Workspace).filter(Workspace.workspace_id == workspace_id).first()
        if workspace:
            workspace.dashboard_state = "[]"
            workspace.chat_history = "[]"
            db.commit()
    finally:
        db.close()
