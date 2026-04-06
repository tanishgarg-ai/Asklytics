# Asklytics 📊
### AI-Powered Intelligence, Redefined.

**Asklytics** is a next-generation Business Intelligence (BI) platform that bridges the gap between complex data and actionable insights. Using high-level AI orchestration, it allows users to connect their databases and generate interactive, real-time dashboards simply by asking questions in natural language.

---

## 🏗️ Architecture & Tech Stack

Asklytics is built with a modern, decoupled architecture designed for scale and performance.

### **Frontend**
- **React + Vite**: For a lightning-fast, reactive user experience.
- **Plotly.js**: Robust, interactive data visualization.
- **React Grid Layout**: Draggable and resizable dashboard components.
- **Tailwind CSS**: Sleek, modern, and responsive UI design.

### **Backend**
- **FastAPI**: High-performance asynchronous Python API.
- **LangGraph**: Advanced agentic orchestration for handling complex natural language intents.
- **Google Gemini**: State-of-the-art LLM for SQL generation and data narration.
- **DuckDB**: Blazing-fast in-memory analytical database for processing query results.
- **PostgreSQL (RDS)**: Persistent storage for workspaces, dashboards, and security.

---

## 🚀 Key Features

- **Natural Language Querying**: No SQL knowledge required. Ask "Show me revenue by region over the last quarter" and see the chart appear instantly.
- **AI-Driven Dashboard Generation**: Automatically generates a starting dashboard upon connecting a database.
- **Interactive Dashboards**: Resize, rearrange, and delete charts with a persistent layout state.
- **Secure Sharing**: Generate time-bound, role-based shareable links (Viewer/Editor) to collaborate with stakeholders.
- **Data Narration**: AI-powered insights that explain the "why" behind the data, not just the "what."
- **Production Ready**: Fully deployed on AWS with Amplify, EC2, and RDS.

---

## 🛠️ Local Development

### **Prerequisites**
- Python 3.9+
- Node.js 18+
- A Google Gemini API Key

### **1. Backend Setup**
Navigate to the `backend` directory:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
Create a `.env` file from `.env.example` and fill in your keys:
```bash
GEMINI_API_KEY=your_key_here
DATABASE_URL=postgresql://user:pass@host:5432/db
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173
```
Run the server:
```bash
python main.py
```

### **2. Frontend Setup**
Navigate to the `frontend` directory:
```bash
cd frontend
npm install
```
Create a `.env` file:
```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```
Run the development server:
```bash
npm run dev
```

---

## ☁️ Deployment

### **AWS Infrastructure**
- **Frontend**: Deployed on **AWS Amplify** for global CDN delivery and automated builds.
- **Backend**: Hosted on **AWS EC2** (Ubuntu/Docker) with a DuckDNS domain for dynamic IP routing.
- **Database**: **AWS RDS (PostgreSQL)** for secure and scalable persistence.

### **Environment Configuration**
Ensure the following environment variables are set in your production environment:
- `VITE_API_BASE_URL`: The URL of your EC2 backend.
- `ALLOWED_ORIGINS`: The URL of your Amplify frontend.
- `FRONTEND_URL`: Used for generating correct share links.

---

## 🔒 Security

Asklytics takes data security seriously:
- **Encrypted Database Credentials**: Your source database URLs are stored using Fernet symmetric encryption.
- **JWT Share Tokens**: Share links are authenticated via short-lived JSON Web Tokens with granular role permissions.
- **CORS Protection**: The API is locked down to authorized origins only.

