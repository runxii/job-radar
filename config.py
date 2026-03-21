import os

# --- Scraper ---
SEARCH_QUERIES = [
    "Software+Engineer",
    "Graduate",
    "QA+Engineer",
    "Test+Engineer",
]
SEARCH_LOCATION = "Ireland"
RESULTS_WANTED = 10        # per keyword; set up to 200 when running for real
HOURS_OLD = 48      # only jobs posted in last 24h

# --- Experience Filter ---
MAX_YEARS_EXPERIENCE = 3   # drop jobs requiring more than this

# --- AI Scorer ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-5-mini"

# Score thresholds
HIGH_MATCH_THRESHOLD = 0.65   # → AI Apply
MID_MATCH_THRESHOLD  = 0.40   # → Human Apply  (below this → Drop)

# --- CV ---
CV_PATH = "cv.txt"
123
# --- Output ---
OUTPUT_EXCEL = "output/jobs.xlsx"
SHEET_RAW       = "raw"
SHEET_MATCHED   = "matched"
SHEET_UNMATCHED = "unmatched"

