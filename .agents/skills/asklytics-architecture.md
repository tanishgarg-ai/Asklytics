---
name: Asklytics Architecture
description: Architecture and design decisions for the Asklytics agentic Business Intelligence platform.
---

# Asklytics Architecture

## Overview
Asklytics is a full-stack, agentic Business Intelligence platform. Users connect their company SQL database, and the AI agent automatically generates a full Power BI-style dashboard. Users can converse with the AI to add new charts. Workspaces are persistent and shareable via role-based links.

## Tech Stack
*   **Frontend**: React, Vite, Tailwind CSS (Glassmorphic aesthetic), react-plotly.js, react-grid-layout
*   **Backend**: Python, FastAPI, DuckDB (query engine), SQLAlchemy (DB source connector), SQLite (workspace persistence)
*   **AI/Agent Engine**: LangGraph, langchain-google-genai (Gemini 2.5 Flash)
*   **Infrastructure**: Docker (Backend), Vercel (Frontend deployment prep)
*   **Package Manager**: pip + requirements.txt

## Core Concept: The Workspace
*   Persistent entity containing user's DB connection URL (encrypted via cryptography.fernet).
*   Chat history with the AI agent.
*   Ordered list of Plotly chart payloads on the dashboard.
*   Role-based sharing ("view" or "edit") via JWT share tokens signed with server's SECRET_KEY.

## Phase 1: Project Scaffolding
### Backend (/backend)
*   **`app/api/`**: API endpoints (`workspaces.py`, `analyze.py`, `agent.py`).
*   **`app/services/`**: Core logic layer (`data_engine.py`, `ingestor.py`, `workspace_store.py`, `crypto.py`).
*   **`app/services/agent/`**: LangGraph AI workflow (`state.py`, `nodes.py`, `graph.py`).
*   **`app/models/`**: Pydantic and SQLAlchemy schemas (`workspace.py`, `chart.py`, `share.py`).
*   **`app/db.py`**: SQLite init.

### Frontend (/frontend)
*   **`src/components/`**: UI components including `Dashboard.jsx`, `ChartTile.jsx`, `ChatPanel.jsx`, etc.
*   **`src/hooks/`**: Custom React hooks (`useWorkspace.js`, `useAgent.js`).
*   **`src/api/`**: Axios client configuration.

## Phase 2: SQLite Workspace Persistence
SQLite is used for lightweight, local persistence of workspaces and share links.
*   **Workspace Table**: Stores workspace UUID, encrypted DB URL, dashboard state (JSON Plotly charts), chat history (JSON messages).
*   **ShareLink Table**: Stores token UUID, workspace FK, role, and expiry.
*   **`workspace_store.py`**: Handles CRUD operations for workspaces and share links.
*   **`crypto.py`**: Handles Fernet encryption/decryption of the DB URL.

## Phase 3: DuckDB Data Engine + SQL Ingestor
*   **Ingestion (`ingestor.py`)**: Connects to the user's DB via SQLAlchemy, reflects tables, and loads them into a DuckDB session via Pandas.
*   **Data Engine (`data_engine.py`)**: Maintains a dictionary mapping workspace IDs to isolated in-memory DuckDB connections. Provides schema retrieval and query execution.

## Phase 4: LangGraph AI Workflow
Orchestrates the LLM to generate SQL, validate against the DB, and construct Plotly JSON payloads.
*   **Nodes**: `SchemaRetriever` -> `QueryGenerator` -> `Validator`.
*   **Error Handling**: If `Validator` fails, flows to `Reflector` to fix the SQL up to 3 times before failing.
*   **Chart Contract**: Strict JSON Plotly payload with transparent background and white font for glassmorphic styling.

## Phase 5: FastAPI Endpoints
*   `POST /api/v1/workspaces`: Initialize workspace, ingest DB, trigger initial 6-8 chart dashboard.
*   `GET /api/v1/workspaces/{workspace_id}`: Load workspace, validate token/header.
*   `POST /api/v1/workspaces/{workspace_id}/chat`: Conversational agent chart generation.
*   `POST /api/v1/workspaces/{workspace_id}/share`: Generate JWT share link.
*   `PUT /api/v1/workspaces/{workspace_id}/settings`: Update settings and regenerate.

## Phase 6: React Frontend
*   **Design**: Glassmorphic aesthetic using Tailwind CSS (e.g., `bg-zinc-950` backgrounds, `bg-white/5 backdrop-blur-md` cards).
*   **Session Management**: JWT token decoding for role-based share links, and `localStorage` for persistent owner sessions.
*   **Core Components**:
    *   **Dashboard**: Utilizes `react-grid-layout` mapping the state of widgets on the screen.
    *   **ChartTile**: Houses the `react-plotly.js` charts as responsive, floating widgets. Employs vanilla CSS resizing (`resize` via Tailwind), flexbox constraints (`min-h-0`), and absolute positioning layers to ensure Plotly SVG charts scale flawlessly in both dimensions without scrollbars. Includes specific optimizations to strip hardcoded dimensions, intelligently hide redundant UI like titles/single-series legends, and vertically align Pie chart legends for optimal container fit.
    *   **ChatPanel**: A slide-out drawer providing a conversational interface with the LangGraph AI agent to incrementally update dashboard queries.
    *   **SchemaExplorer**: An interactive sidebar to view the structured schema reflected from the user's database.
