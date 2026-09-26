# StravaToExcel
StravaToExcel processes exported Strava running activities and generates summary tables in CSV and Excel format. It extracts fields such as distance, pace, heart rate, cadence, calories, and time spent in heart rate and pace zones, transforming them into a format ready for spreadsheet analysis.

# Installation

Clone the repository:

```
git clone https://github.com/Tristan1118/StravaToExcel.git
cd StravaToExcel
```

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then create the virtual environment and install the dependencies:

```
uv sync
```

# Usage

## 1. Credentials

Create an API application at https://www.strava.com/settings/api and set its **Authorization Callback Domain** to `localhost`.

Copy `.env.example` to `.env` and fill in the client ID and secret:

```
STRAVA_CLIENT_ID=XXXXX
STRAVA_CLIENT_SECRET=XXXXXXXXXXXXXXXXXXXXXXXXX
```

The variables can also be set in the environment directly, which takes precedence over `.env`.

## 2. Log in (once)

```
uv run authenticate.py --login
```

This opens Strava in the browser. After you approve access, the tokens are saved to `auth.json`. The exporter refreshes the access token automatically when it expires, so this only needs to be repeated if the refresh token is revoked.

## 3. Export activities

```
uv run exporter.py
```

Activity details are saved to `activities/` and heart rate / pace zones to `zones/`, one JSON file per activity ID.

The exporter only asks Strava for activities that started after the newest activity already in `activities/`, so after the first run it makes a single list request plus one request per new activity. Requests are throttled to stay within Strava's rate limits.

Use `--all` to list every activity again. Existing files are still skipped, so this only fills gaps, e.g. after an interrupted first run or a failed zones download:

```
uv run exporter.py --all
```

Edits to activities that were already downloaded (renames, marking a run as a race) are not picked up. Delete the activity's file in `activities/` and run `uv run exporter.py --all` to download it again.

## 4. Generate the table

```
uv run generate_table.py
```

This writes `output/strava_summary.csv` and `output/strava_summary.xlsx`, overwriting the previous files.

## Tests

```
uv run pytest
```

# Project Structure

```
StravaToExcel/
-- activities/        # Activity JSON files
-- zones/             # Zone JSON files
-- output/            # Generated CSV and Excel files
-- tests/             # pytest tests
-- pyproject.toml     # Dependencies (locked in uv.lock)
-- authenticate.py    # Strava login and token refresh
-- exporter.py        # Downloads activities and zones from Strava
-- generate_table.py  # Builds the CSV and Excel tables from the JSON files
-- README.md
```

# Notes

Only activities with sport_type == "Run" are processed. If a zone file is missing, the corresponding zone columns will be left empty.
