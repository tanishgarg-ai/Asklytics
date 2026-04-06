import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from dotenv import load_dotenv

load_dotenv()

from app.api import workspaces

app = FastAPI(title="Asklytics API", version="1.0")

# CORS setup
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    origins = [o.strip() for o in allowed_origins_env.split(",")]
else:
    origins = [
        "https://master.d180ha7an42ujc.amplifyapp.com",
        "http://localhost:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Explicit preflight handler (fixes OPTIONS 400 issue)
@app.options("/{rest_of_path:path}")
async def preflight_handler():
    return Response(status_code=200)

# ✅ Routes
app.include_router(workspaces.router)

@app.get("/health")
def health():
    """
    Health check endpoint for the API.

    Returns:
        dict: A dictionary containing the API status.
    """
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
