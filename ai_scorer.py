"""
Stage 4 - AI Scorer
Sends each matched job + CV to OpenAI for fit scoring.
Ported from the n8n "Message a model" + "Parse AI output" nodes.
"""
from __future__ import annotations
import json
import time
import re
import config

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # allow import in test environments without openai installed


_SYSTEM_PROMPT = (
    "You are a senior HR in Ireland."
    "Rate how well the candidate fits this job based on full experience."
)

_USER_TEMPLATE = """
Eval job vs candidate.

Classify role:
- tech
- tech_adj
- product
- customer_ops

Reject if JD explicitly requires:
- non EN/Chinese
- non-CS degree
- EU/EEA citizen, Stamp 4


If reject:
{{"id":"{job_id}","rf":"x","tm":0.00,"rm":0.00,"dm":0.00,"fit":0.00,"hd":1}}

Compare with candidate facts only.

Scoring:
tech: fit=avg(tm,rm,es)
product: fit=avg(dm,rm,cm)
customer_ops: fit=avg(ce,rm,op)
tech_adj: fit=avg(tm,rm,cm)

Caps if no direct evidence:
- customer_ops max 0.35
- product max 0.55
- tech_adj max 0.65

Use exact evidence, not general professionalism.
Do not treat teamwork/docs/delivery alone as customer or product evidence.
Only use given data.
JSON only:
{{"id": "{job_id}", "stack_match": 0.00, "res_match": 0.00, "engi_match": 0.00, "overall_fit": 0.00}}

Candidate Experience:
{cv}

Job Description:
{title}
{description}
""".strip()


def _label(score: float) -> str:
    if score >= config.high_matched_THRESHOLD:
        return "high_matched"
    if score >= config.MID_MATCH_THRESHOLD:
        return "mid_matched"
    return "Drop"


def _parse_response(raw_text: str) -> dict:
    """Extract JSON from model response (handles minor formatting noise)."""
    # strip markdown fences if present
    cleaned = re.sub(r"```[a-z]*\n?", "", raw_text).strip()
    return json.loads(cleaned)


def score_job(job: dict, cv: str, client) -> dict:
    """Score a single job. Returns dict with match fields added."""
    prompt = _USER_TEMPLATE.format(
        job_id=job["id"],
        cv=cv,
        title=job.get("title", ""),
        description=job.get("description", ""),
    )

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )

    raw = response.choices[0].message.content
    parsed = _parse_response(raw)

    result = dict(job)
    result["match_score"] = parsed.get("overall_fit", 0.0)
    result["skills_required"] = json.dumps({
        "stack":          parsed.get("stack_match"),
        "responsibility": parsed.get("res_match"),
        "engineering":    parsed.get("engi_match"),
    })
    result["status"] = _label(result["match_score"])
    return result


def score_jobs(
    jobs: list[dict],
    cv: str,
    delay_seconds: float = 1.0,
) -> list[dict]:
    """Score all jobs with rate-limit delay between calls."""
    if OpenAI is None:
        raise RuntimeError("openai package not installed - run: pip install openai")
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in environment or config.py")

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    results: list[dict] = []

    for i, job in enumerate(jobs, 1):
        print(f"[scorer] {i}/{len(jobs)} scoring job {job.get('id')} ...")
        try:
            scored = score_job(job, cv, client)
            results.append(scored)
        except Exception as exc:
            print(f"[scorer] WARNING: job {job.get('id')} failed - {exc}")
            result = dict(job)
            result.update({"match_score": 0.0, "skills_required": {}, "status": "Drop"})
            results.append(result)
        time.sleep(delay_seconds)

    return results


def load_cv(path: str = config.CV_PATH) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().replace("\u000b", "").strip()
