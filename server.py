"""
server.py - FastAPI mini app for reviewing job cards.

Usage:
    SUPABASE_URL=... SUPABASE_KEY=... uvicorn server:app --reload

Then open http://localhost:8000 in your browser.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import db
import os

app = FastAPI(title="JobRadar")

VALID_USER_STATUSES = {"Applied", "Skipped", "Saved"}


# --------------------------------------------------------------------------- #
# API routes                                                                   #
# --------------------------------------------------------------------------- #

@app.get("/api/jobs/next")
def next_job():
    job = db.fetch_next_job()
    if job is None:
        return {"done": True}
    return job


@app.get("/api/jobs")
def all_jobs(limit: int = 200):
    return db.fetch_all_jobs(limit)


@app.get("/api/stats")
def stats():
    return db.fetch_stats()


class StatusUpdate(BaseModel):
    status: str


@app.post("/api/jobs/{job_id}/status")
def update_status(job_id: str, body: StatusUpdate):
    if body.status not in VALID_USER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {VALID_USER_STATUSES}"
        )
    db.update_status(job_id, body.status)
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Frontend                                                                     #
# --------------------------------------------------------------------------- #

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()