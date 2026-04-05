import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./asklytics.db")

# For production/RDS, we want to ensure stale connections are handled correctly.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args,
    pool_pre_ping=True  # Important for RDS to recover from idle connection drops
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Workspace(Base):
    """
    SQLAlchemy model representing a user workspace.

    Stores the workspace identifier, an encrypted connection string to the source database,
    and the serialized dashboard configuration and chat history.
    """
    __tablename__ = "workspaces"

    workspace_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    encrypted_db_url = Column(String, nullable=False)
    dashboard_state = Column(String, default="[]")
    chat_history = Column(String, default="[]")


class ShareLink(Base):
    """
    SQLAlchemy model representing an invitation or access token.

    Manages timed access to workspaces by issuing tokens with specific roles 
    and expiration bounds.
    """
    __tablename__ = "share_links"

    token_id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)


Base.metadata.create_all(bind=engine)
