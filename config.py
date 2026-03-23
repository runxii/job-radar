import os

# --- Scraper ---
SEARCH_QUERIES = [
    "Software+Engineer",
    "Graduate",
    "QA+Engineer",
    "Test+Engineer",
]
SEARCH_LOCATION = "Ireland"
RESULTS_WANTED = 20        # per keyword; set up to 200 when running for real
HOURS_OLD = 72      # only jobs posted in last 24h

# --- Experience Filter ---
MAX_YEARS_EXPERIENCE = 3   # drop jobs requiring more than this

# --- AI Scorer ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-5-mini"

# Score thresholds
HIGH_MATCH_THRESHOLD = 0.7   # → high_matched
MID_MATCH_THRESHOLD  = 0.40   # → mid_matched  (below this → Drop)

# --- CV ---
CV_PATH = "cv.txt"


# --- Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
 
