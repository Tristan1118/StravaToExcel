# StravaToExcel
StravaToExcel exports Strava activities and generates summary tables in CSV and Excel format: one for runs and one for all other activity types. It extracts fields such as distance, pace, heart rate, cadence, calories, and time spent in heart rate and pace zones, transforming them into a format ready for spreadsheet analysis.

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

Upgrading from an older version: `client.json` is no longer read. Move its two values into `.env` and delete the file.

## 2. Log in (once)

```
uv run authenticate.py --login
```

This opens Strava in the browser and requests the `read` and `activity:read_all` scopes, so private activities are included. After you approve access, the tokens are saved to `auth.json`. The exporter refreshes the access token automatically when it expires, so this only needs to be repeated if the refresh token is revoked.

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

Strava allows 1,000 read requests per day and the exporter needs two per activity (details and zones), so a first run over a large history (roughly 500+ activities) stops when the daily limit is reached. The newest activities are downloaded first. Continue the next day (the limit resets at midnight UTC) with `uv run exporter.py --all`; without `--all`, only activities newer than the ones already downloaded would be listed.

Edits to activities that were already downloaded (renames, marking a run as a race) are not picked up. Delete the activity's file in `activities/` and run `uv run exporter.py --all` to download it again.

## 4. Generate the tables

```
uv run generate_table.py
```

This writes two tables to `output/` as CSV and Excel, overwriting the previous files:

- `strava_runs.csv` / `.xlsx`: activities with sport type `Run`, including pace, cadence, race flag, and heart rate and pace zones.
- `strava_other.csv` / `.xlsx`: all other activity types (rides, hikes, swims, weight training, ...) with a `Sport Type` column, average speed in km/h, average watts, and heart rate zones. Fields that don't apply to an activity, such as distance for weight training, are left empty.

Both tables are sorted by start date. The CSV files are UTF-8 with a BOM so that Excel shows special characters in activity names correctly. When reading them with Python's `csv` module, open them with `encoding='utf-8-sig'` (pandas handles this automatically).

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
-- .env.example       # Template for .env (Strava client ID and secret)
-- .env               # Your credentials (not committed)
-- auth.json          # Access and refresh tokens, written by authenticate.py (not committed)
-- pyproject.toml     # Dependencies
-- uv.lock            # Locked dependency versions
-- authenticate.py    # Strava login and token refresh
-- exporter.py        # Downloads activities and zones from Strava
-- generate_table.py  # Builds the CSV and Excel tables from the JSON files
-- README.md
```

# Notes

If a zone file is missing, the corresponding zone columns will be left empty.
