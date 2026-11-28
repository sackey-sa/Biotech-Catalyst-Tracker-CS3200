"""FastAPI app for the Biotech Catalyst Tracker frontend. Read-only: every endpoint is a GET
except running a saved showcase query, and none of them change data.

Run from the repo root:
    uvicorn backend.main:app --reload --port 8000
Interactive docs: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import companies, events, queries, stats, trials

app = FastAPI(title="Biotech Catalyst Tracker API", version="0.1.0")

# The Vite dev server proxies /api, but allow direct calls from it too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

for router in (stats.router, events.router, companies.router, trials.router, queries.router):
    app.include_router(router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
