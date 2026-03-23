# 📡 JobRadar

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--API-412991?style=flat&logo=openai&logoColor=white)
![JobSpy](https://img.shields.io/badge/Scraper-JobSpy-0A66C2?style=flat)
![Excel](https://img.shields.io/badge/Output-Excel%20(.xlsx)-217346?style=flat&logo=microsoftexcel&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-pytest-brightgreen?style=flat&logo=pytest)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

> An end-to-end job search automation pipeline that scrapes LinkedIn daily, filters out roles you'll never get, and uses AI to score the ones worth applying to — all saved to a local Excel file.

---

## How It Works

```
LinkedIn (JobSpy)
      │
      ▼
  Stage 1: Scrape         — fetch up to 200 jobs per keyword
      │
      ▼
  Stage 2: Clean & Dedup  — normalise schema, remove duplicates
      │
      ▼
  Stage 3: Exp. Filter    — regex extracts required years; drops senior roles
      │
      ├──► unmatched sheet
      │
      ▼
  Stage 4: AI Scoring     — GPT-4o-mini scores each job against your CV
      │
      ▼
  Stage 5: Excel Output   — upsert into jobs.xlsx (raw / matched / unmatched)
```

Each run is **incremental** — jobs already recorded in a previous run are skipped automatically.

---

## Quickstart

### 1. Clone & install

```bash
git clone https://github.com/runxii/job-radar.git
cd job-radar
pip install -r requirements.txt
```

### 2. Add your CV

Create a `cv.txt` in root, and paste your CV as plain text into `cv.txt`. The AI scorer reads this file to evaluate your fit against each job description.

```
cv.txt
──────
Name: Your Name
Education: BSc Computer Science, 2024
Skills: Python, React, Node.js, PostgreSQL, Docker ...
Experience: ...
```

### 3. Set your OpenAI API key

```bash
# Mac / Linux
export OPENAI_API_KEY=sk-...

# Permanent set in Linux
echo "export OPENAI_API_KEY=sk-..." >> ~/.bashrc

# Windows (PowerShell)
setx OPENAI_API_KEY sk-...
```

### 4. Run

```bash
python main.py
```

Output is saved to `output/jobs.xlsx` with three sheets:

| Sheet | Contents |
|---|---|
| `raw` | Every job scraped, unfiltered |
| `matched` | Jobs that passed the experience filter, with AI scores and status |
| `unmatched` | Jobs filtered out (too senior, wrong role type, etc.) |

---

## Configuration

All tunable parameters live in `config.py`:

### Search

| Parameter | Default | Description |
|---|---|---|
| `SEARCH_QUERIES` | `["Software Engineer", "Graduate Engineer", ...]` | Keywords sent to LinkedIn. Add or remove as needed. |
| `SEARCH_LOCATION` | `"Ireland"` | Location string passed to JobSpy. |
| `RESULTS_WANTED` | `50` | Max results per keyword. Up to 200 supported. |
| `HOURS_OLD` | `24` | Only return jobs posted within this many hours. |

### Experience Filter

| Parameter | Default | Description |
|---|---|---|
| `MAX_YEARS_EXPERIENCE` | `3` | Jobs requiring more than this many years are sent to `unmatched`. |

### AI Scoring

| Parameter | Default | Description |
|---|---|---|
| `OPENAI_MODEL` | `"gpt-5-mini"` | Model used for scoring. Swap to `gpt-5` for higher accuracy. |
| `high_matched_THRESHOLD` | `0.65` | Score at or above this → `high_matcheded` |
| `MID_MATCH_THRESHOLD` | `0.40` | Score at or above this → `mid_matched`. Below → `Drop` |

### Output

| Parameter | Default | Description |
|---|---|---|
| `CV_PATH` | `"cv.txt"` | Path to your CV text file. |
| `OUTPUT_EXCEL` | `"output/jobs.xlsx"` | Path to the output workbook. |

---

## AI Scoring Logic

Each job is scored across three axes, then averaged into `overall_fit`:

| Axis | What it measures |
|---|---|
| `stack_match` | Overlap between JD's tech stack and your CV |
| `responsibility_match` | How closely the day-to-day work matches your experience |
| `engineering_signal_match` | Depth of engineering culture vs support/ops role |

### Score calibration

| Score | Label | Meaning |
|---|---|---|
| ≥ 0.65 | **high_matcheded** | Strong fit — meets most requirements |
| 0.40 – 0.64 | **mid_matched** | Partial fit — worth reviewing manually |
| < 0.40 | **Drop** | Poor fit — fundamental mismatch |
| 0.00 | **Hard disqualified** | Triggered a hard disqualifier (see below) |

### Hard disqualifiers

A job scores `0.00` immediately if any of the following are detected:

- Mandatory spoken/written language other than English or Chinese
- Mandatory degree requirement outside computer science
- Role is primarily non-technical (customer service, sales, HR, etc.)
- Explicitly requires Stamp 4 or EU/EEA citizenship as mandatory

---

## Project Structure

```
JobRadar/
├── main.py                  # Pipeline orchestrator
├── config.py                # All tunable settings
├── scraper.py               # Stage 1 — JobSpy LinkedIn scraper
├── cleaner.py               # Stage 2 — schema normalisation & dedup
├── experience_filter.py     # Stage 3 — regex year extraction & filtering
├── ai_scorer.py             # Stage 4 — OpenAI scoring
├── excel_writer.py          # Stage 5 — Excel upsert writer
├── cv.txt                   # Your CV (plain text)
├── requirements.txt
├── output/
│   └── jobs.xlsx            # Generated on first run
└── tests/
    ├── test_scraper.py
    ├── test_cleaner.py
    ├── test_experience_filter.py
    ├── test_ai_scorer.py
    └── test_excel_writer.py
```

---

## Running Tests

```bash
pytest tests/ -v
```

53 unit tests across all 5 modules. External APIs (JobSpy, OpenAI) are fully mocked — no API key or internet connection required to run the test suite.

---

## Requirements

- Python 3.10+
- OpenAI API key
- No LinkedIn account required (JobSpy scrapes public listings)

```
python-jobspy
openai>=1.0.0
openpyxl>=3.1.0
pandas>=2.0.0
pytest>=7.0.0
```

---

## License

MIT
