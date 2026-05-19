import os

# --- Main ---

BATCH_SIZE = 10

# --- Scraper ---
SEARCH_QUERIES = [
    "Software+Engineer",
    "Graduate",
    "Web+Developer",
    "Full+Stack",
]
SEARCH_LOCATION = "Ireland"
RESULTS_WANTED = 20  # per keyword; set up to 200 when running for real
HOURS_OLD = 24  # only jobs posted in last 24h

# --- Filter ---
MAX_YEARS_EXPERIENCE = 3  # drop jobs requiring more than this
BLACKLIST_COMPANIES = {
    "DataAnnotation",
    "Mindrift",
    "Bending Spoons",
    "Jobgether",
}

# --- AI Scorer ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-5-mini"

# Score thresholds
high_matched_THRESHOLD = 0.70  # → high_matched
MID_MATCH_THRESHOLD = 0.45  # → mid_matched  (below this → Drop)

# --- CV ---
CV_PATH = "cv.txt"


# --- Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
