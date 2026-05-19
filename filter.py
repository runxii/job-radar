"""
Stage 3 - Filter
Ported from the n8n JS node "Work Experience Demand Abstract".

- Detects senior titles (principal / lead / head / director / manager) → marks as 10 yrs
- Extracts explicit numeric year requirements from description via regex
- Drops suspicious/unreliable company posts into unmatched
- Splits jobs into matched and unmatched
"""

from __future__ import annotations
import re
import config


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

_SENIOR_KEYWORDS = re.compile(
    r"\b(principal|lead|head|director|manager|leader)\b", re.IGNORECASE
)

# Ordered list of patterns - first match with the lowest year wins.
_YEAR_PATTERNS: list[re.Pattern] = [
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
    # generic fallback: 5 years in software development / 5-years industry experience / 3-5 years as a professional
    re.compile(
        r"(?:\d{1,2}\s*[-–]\s*)?(\d{1,2})\s*years?'?\s*(?:of\s+|in\s+|with\s+|as\s+)?(?:\w+\s+){0,8}\b",
        re.I,
    ),
    # requires 8 years with/in/of
    re.compile(
        r"(?:requires?|need(?:s|ed)?|seeking)\s+(\d{1,2})(?:\\?\+)?\s*years?\s+(?:of|in|with)\b",
        re.I,
    ),
]


def _normalize(text: str) -> str:
    text = repr(text)
    text = text.replace("\u00a0", " ")
    text = text.replace(r"\+", "+")
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()


def _blacklisted_companies() -> set[str]:
    """
    Reads custom blacklist company names from config.py.

    Expected config.py:
        BLACKLIST_COMPANIES = {"company a", "company b"}

    Matching is case-insensitive and exact after stripping whitespace.
    """
    companies = getattr(config, "BLACKLIST_COMPANIES", set())

    return {
        str(company).strip().lower() for company in companies if str(company).strip()
    }


def company_is_blacklisted(job: dict) -> bool:
    company = (
        job.get("company")
        or job.get("company_name")
        or job.get("companyName")
        or job.get("employer")
        or job.get("organization")
        or ""
    )

    company = str(company).strip().lower()

    if not company:
        return False

    return company in _blacklisted_companies()


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


def filter(
    jobs: list[dict],
    max_years: int = config.MAX_YEARS_EXPERIENCE,
) -> tuple[list[dict], list[dict]]:
    """
    Returns (matched, unmatched).

    matched:
        explicit_years_required <= max_years
        and company is not in config.BLACKLIST_COMPANIES

    unmatched:
        explicit_years_required > max_years
        or company is in config.BLACKLIST_COMPANIES
    """
    annotated = [annotate_experience(j) for j in jobs]

    matched = [
        j
        for j in annotated
        if j["explicit_years_required"] <= max_years and not company_is_blacklisted(j)
    ]

    unmatched = [
        j
        for j in annotated
        if j["explicit_years_required"] > max_years or company_is_blacklisted(j)
    ]

    print(
        f"[filter] {len(matched)} matched, {len(unmatched)} unmatched "
        f"(threshold <={max_years} yrs, blacklist={len(_blacklisted_companies())})"
    )

    return matched, unmatched


filter_by_experience = filter
