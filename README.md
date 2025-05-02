# StravaToExcel
StravaToExcel processes exported Strava running activities and generates summary tables in CSV and Excel format. It extracts fields such as distance, pace, heart rate, cadence, calories, and time spent in heart rate and pace zones, transforming them into a format ready for spreadsheet analysis.

# Installation

Clone the repository:

```
git clone https://github.com/Tristan1118/StravaToExcel.git
cd StravaToExcel
```

Install dependencies:

```
pip install pandas
```

# Usage

Place your client key and secret in client.json

```
{
  "client_id": "XXXXX",
  "client_secret": "XXXXXXXXXXXXXXXXXXXXXXXXX"
}
```

Generate a refresh token and place the auth material in auth.json:

```
{
  "token_type": "Bearer",
  "access_token": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "expires_at": XXXXXXX,
  "expires_in": XXXXX,
  "refresh_token": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
}
```

Refresh token with authenticate.py.


Export your Strava activities and place the activity JSON files into the activities/ folder and the matching zone JSON files into the zones/ folder. Filenames must match by activity ID.

Export activities:

```
python exporter.py
```

Generate tables from activities on disk:

```
python generate_table.py
```

The output files will be saved in the output/ directory with the current timestamp in the filename.

# Project Structure

```
StravaToExcel/
-- activities/        # Activity JSON files
-- zones/             # Zone JSON files
-- output/            # Generated CSV and Excel files
-- generate_table.py  # Main script to process activities
-- exporter.py        # Helper script to export tables
-- README.md
```

# Notes

Only activities with sport_type == "Run" are processed. If a zone file is missing, the corresponding zone columns will be left empty.
