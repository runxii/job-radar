"""
server.py - FastAPI mini app for reviewing job cards.

Usage:
    SUPABASE_URL=... SUPABASE_KEY=... uvicorn server:app --reload

Then open http://localhost:8000
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import db
import os

app = FastAPI(title="JobRadar")

ALL_STATUSES = {"high_matched", "mid_matched", "Applied", "Skipped", "Saved", "Drop"}


# --------------------------------------------------------------------------- #
# API                                                                          #
# --------------------------------------------------------------------------- #

@app.get("/api/jobs/next")
def next_job():
    job = db.fetch_next_job()
    if job is None:
        return {"done": True}
    return job


@app.get("/api/jobs")
def all_jobs(status: str | None = None, limit: int = 200):
    if status:
        return db.fetch_jobs_by_status(status, limit)
    return db.fetch_all_jobs(limit)


@app.get("/api/stats")
def stats():
    return db.fetch_stats()


class StatusUpdate(BaseModel):
    status: str


@app.post("/api/jobs/{job_id}/status")
def update_status(job_id: str, body: StatusUpdate):
    if body.status not in ALL_STATUSES:
        raise HTTPException(400, detail=f"Invalid status: {body.status}")
    db.update_status(job_id, body.status)
    return {"ok": True}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    db.delete_job(job_id)
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Frontend                                                                     #
# --------------------------------------------------------------------------- #

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()