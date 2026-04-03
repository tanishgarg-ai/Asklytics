import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./asklytics.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Workspace(Base):
    __tablename__ = "workspaces"

    workspace_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    encrypted_db_url = Column(String, nullable=False)
    dashboard_state = Column(String, default="[]")
    chat_history = Column(String, default="[]")


class ShareLink(Base):
    __tablename__ = "share_links"

    token_id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)


Base.metadata.create_all(bind=engine)
