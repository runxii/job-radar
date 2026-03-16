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
    "Act as a senior engineer. "
    "Rate how well the candidate fits this job based on full experience."
)

_USER_TEMPLATE = """
1. Hard disqualifiers (evaluate first, immediately output overall_fit = 0.00 and hard_disqualify = true if ANY applies):
- Job title or JD requires a spoken/written language other than English or Chinese as mandatory
- Degree requirement is mandatory AND not computer science related
- EU/EEA citizenship or work permit sponsorship is explicitly stated as NOT available (i.e. candidate must already hold right to work)

If no hard disqualifier:
2. Extract core technical stack.
3. Extract main responsibilities.
4. Compare against candidate experience.
5. Score:
   - stack_match (0-1)
   - responsibility_match (0-1)
   - engineering_signal_match (0-1)
   - overall_fit = average of the three

   Scoring calibration:
   - 0.7 and above: strong fit, candidate meets most requirements
   - 0.4 to 0.69: partial fit, candidate meets some but has clear gaps
   - below 0.4: poor fit, fundamental mismatch in role type or required experience
   - 0.0: hard disqualified (see above)
6. Be strict for senior roles.

Return single-line JSON only — no markdown, no explanation:

{{"id": "{job_id}", "stack_match": 0.00, "res_match": 0.00, "engi_match": 0.00, "overall_fit": 0.00}}

Candidate Experience:
{cv}

Job Description:
{title}
{description}
""".strip()


def _label(score: float) -> str:
    if score >= config.HIGH_MATCH_THRESHOLD:
        return "AI Apply"
    if score >= config.MID_MATCH_THRESHOLD:
        return "Human Apply"
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
            result.update({"match_score": 0.0, "skills_required": "{}", "status": "Drop"})
            results.append(result)
        time.sleep(delay_seconds)

    return results


def load_cv(path: str = config.CV_PATH) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().replace("\u000b", "").strip()
