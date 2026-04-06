import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# Fetch from environment, fallback to sqlite for extreme local testing edge-cases
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./asklytics.db")

connect_args = {}

# SQLite requires a specific argument to prevent threading errors.
# Postgres (psycopg2) does not need this, but might need SSL arguments
# if they aren't parsed directly from the URL.
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgres"):
    # If the URL string params (?sslmode=...) fail on AWS, uncomment below:
    # connect_args = {
    #     "sslmode": "verify-full",
    #     "sslrootcert": "./global-bundle.pem"
    # }
    pass

# Create the SQLAlchemy Engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True  # CRITICAL FOR AWS RDS: Recovers gracefully if RDS drops an idle connection
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


# 🚀 AWS / FRESH START MAGIC LINE 🚀
# Because you are starting fresh and not using Alembic migrations yet,
# this line tells SQLAlchemy to inspect the classes above and automatically
# create the empty 'workspaces' and 'share_links' tables in your AWS Postgres DB.
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables validated/created successfully.")
except Exception as e:
    print(f"Failed to create tables: {e}")