"""
Stage 3 - Experience Filter
Ported from the n8n JS node "Work Experience Demand Abstract".

- Detects senior titles (principal / lead / head / director / manager) → marks as 10 yrs
- Extracts explicit numeric year requirements from description via regex
- Splits jobs into matched (≤ MAX_YEARS) and unmatched (> MAX_YEARS)
"""

from __future__ import annotations
import re
import config


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

_SENIOR_KEYWORDS = re.compile(
    r"\b(principal|lead|head|director|manager)\b", re.IGNORECASE
)

# Ordered list of patterns - first match with the lowest year wins.
_YEAR_PATTERNS: list[re.Pattern] = [
    # 3-5 years of experience / 5-10 years' experience
    re.compile(
        r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s*years?'?\s*(?:of\s+|in\s+|with\s+)?(?:\w+\s+){0,6}?experience\b",
        re.I,
    ),
    # minimum 5 years / at least 7 years / more than 10 years
    re.compile(
        r"(?:minimum|min\.?|at\s+least|over|more\s+than)\s+(?:of\s+)?(\d{1,2})\s+(?:consecutive\s+)?years?\b",
        re.I,
    ),
    # 3+ years of experience / 5 years relevant experience / 7\+ years' experience
    re.compile(
        r"(\d{1,2})(?:\\?\+)?\s*years?\u2019?\s*(?:of\s+|in\s+|with\s+)?(?:\w+\s+){0,6}?experience\b",
        re.I,
    ),
    # 10+ yoe
    re.compile(
        r"(\d{1,2})(?:\\?\+)?\s*yoe\b",
        re.I,
    ),
    # generic fallback: 5 years in software development / 5-years industry experience
    re.compile(
        r"(\d{1,2})\s*-?\s*years?'?\s*(?:of\s+|in\s+|with\s+)?(?:\w+\s+){0,6}?(?:experience|experiences)\b",
        re.I,
    ),
    # requires 8 years with/in/of
    re.compile(
        r"(?:requires?|need(?:s|ed)?|seeking)\s+(\d{1,2})(?:\\?\+)?\s*years?\s+(?:of|in|with)\b",
        re.I,
    ),
]


def _normalize(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()


def title_implies_senior(title: str) -> bool:
    return bool(_SENIOR_KEYWORDS.search(title or ""))


def extract_explicit_years(text: str) -> dict:
    """
    Returns {"years": int, "explicit": bool, "evidence": str}
    """
    s = _normalize(text or "")
    best: dict | None = None

    for pattern in _YEAR_PATTERNS:
        for match in pattern.finditer(s):
            try:
                n = int(match.group(1))
            except (IndexError, ValueError):
                continue
            if not (0 < n <= 40):
                continue
            start = max(0, match.start() - 50)
            end = min(len(s), match.end() + 100)
            evidence = s[start:end][:220]
            if best is None or n < best["years"]:
                best = {"years": n, "explicit": True, "evidence": evidence}

    return best or {"years": 0, "explicit": False, "evidence": ""}


def annotate_experience(job: dict) -> dict:
    """Add experience fields to a job dict (mutates a copy)."""
    job = dict(job)
    title = job.get("title", "")

    if title_implies_senior(title):
        job["explicit_years_required"] = 10
        job["is_explicit_exp_requirement"] = False
        job["exp_evidence"] = title
        return job

    result = extract_explicit_years(job.get("description", ""))
    job["explicit_years_required"] = result["years"]
    job["is_explicit_exp_requirement"] = result["explicit"]
    job["exp_evidence"] = result["evidence"]
    return job


def filter_by_experience(
    jobs: list[dict],
    max_years: int = config.MAX_YEARS_EXPERIENCE,
) -> tuple[list[dict], list[dict]]:
    """
    Returns (matched, unmatched).
    matched   → explicit_years_required <= max_years  (goes forward to AI scoring)
    unmatched → explicit_years_required >  max_years  (recorded and discarded)
    """
    annotated = [annotate_experience(j) for j in jobs]
    matched = [j for j in annotated if j["explicit_years_required"] <= max_years]
    unmatched = [j for j in annotated if j["explicit_years_required"] > max_years]
    print(
        f"[filter] {len(matched)} matched, {len(unmatched)} unmatched (threshold <={max_years} yrs)"
    )
    return matched, unmatched
