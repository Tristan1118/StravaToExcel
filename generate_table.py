import os
import json
import pandas as pd
from datetime import datetime, timedelta

ACTIVITIES_DIR = './activities'
ZONES_DIR = './zones'
OUTPUT_DIR = './output'
RUNS_NAME = 'strava_runs'
OTHER_NAME = 'strava_other'

RUN_COLUMNS = [
    'Activity ID', 'Name', 'Start Date (Local)', 'Distance (m)', 'Moving Time (s)',
    'Elevation Gain (m)', 'Pace (min/km)', 'Avg Heart Rate', 'Max Heart Rate', 'Avg Cadence (steps/min)', 'Calories', 'Race'
] + [f'Heart Rate - Zone {i}' for i in range(1, 6)] + [f'Pace - Zone {i}' for i in range(1, 7)]

OTHER_COLUMNS = [
    'Activity ID', 'Name', 'Sport Type', 'Start Date (Local)', 'Distance (m)', 'Moving Time (s)',
    'Elevation Gain (m)', 'Avg Speed (km/h)', 'Avg Heart Rate', 'Max Heart Rate', 'Calories', 'Avg Watts'
] + [f'Heart Rate - Zone {i}' for i in range(1, 6)]


def format_start_date(activity_data):
    start_date_local = activity_data.get('start_date_local')
    if not start_date_local:
        return None
    return datetime.fromisoformat(start_date_local).strftime('%Y-%m-%d %H:%M:%S')


def build_run_row(activity_data, zone_data):
    row = {}

    # Basic fields
    row['Activity ID'] = activity_data.get('id')
    row['Name'] = activity_data.get('name')
    row['Distance (m)'] = activity_data.get('distance')
    row['Moving Time (s)'] = str(timedelta(seconds=activity_data.get('moving_time', 0)))
    row['Elevation Gain (m)'] = activity_data.get('total_elevation_gain')
    row['Start Date (Local)'] = format_start_date(activity_data)

    # Average speed for Pace (min/km)
    avg_speed = activity_data.get('average_speed')
    if avg_speed and avg_speed > 0:
        pace_min_per_km = (1000 / avg_speed) / 60
        minutes = int(pace_min_per_km)
        seconds = int((pace_min_per_km - minutes) * 60)
        row['Pace (min/km)'] = f"{minutes}:{seconds:02d}"
    else:
        row['Pace (min/km)'] = None

    # Heart rate and calories
    row['Avg Heart Rate'] = activity_data.get('average_heartrate')
    row['Max Heart Rate'] = activity_data.get('max_heartrate')
    row['Calories'] = activity_data.get('calories')

    # Cadence
    avg_cadence = activity_data.get('average_cadence')
    if avg_cadence:
        row['Avg Cadence (steps/min)'] = avg_cadence * 2
    else:
        row['Avg Cadence (steps/min)'] = None

    # Race detection
    workout_type = activity_data.get('workout_type')
    row['Race'] = 'Yes' if workout_type == 1 else 'No'

    # Add heart rate and pace zone times
    for zone in zone_data:
        if zone.get('type') == 'heartrate':
            for i, bucket in enumerate(zone.get('distribution_buckets', [])[:5], start=1):
                row[f'Heart Rate - Zone {i}'] = bucket.get('time', 0)
        elif zone.get('type') == 'pace':
            for i, bucket in enumerate(zone.get('distribution_buckets', [])[:6], start=1):
                row[f'Pace - Zone {i}'] = bucket.get('time', 0)

    return row


def build_other_row(activity_data, zone_data):
    row = {}

    row['Activity ID'] = activity_data.get('id')
    row['Name'] = activity_data.get('name')
    row['Sport Type'] = activity_data.get('sport_type')
    row['Start Date (Local)'] = format_start_date(activity_data)
    # Strava reports 0 for activities without GPS (e.g. weight training), leave those empty
    row['Distance (m)'] = activity_data.get('distance') or None
    row['Moving Time (s)'] = str(timedelta(seconds=activity_data.get('moving_time', 0)))
    row['Elevation Gain (m)'] = activity_data.get('total_elevation_gain') or None

    avg_speed = activity_data.get('average_speed')
    row['Avg Speed (km/h)'] = round(avg_speed * 3.6, 2) if avg_speed else None

    row['Avg Heart Rate'] = activity_data.get('average_heartrate')
    row['Max Heart Rate'] = activity_data.get('max_heartrate')
    row['Calories'] = activity_data.get('calories')
    row['Avg Watts'] = activity_data.get('average_watts')

    for zone in zone_data:
        if zone.get('type') == 'heartrate':
            for i, bucket in enumerate(zone.get('distribution_buckets', [])[:5], start=1):
                row[f'Heart Rate - Zone {i}'] = bucket.get('time', 0)

    return row


def to_dataframe(rows, column_order):
    df = pd.DataFrame(rows)
    df = df.reindex(columns=[col for col in column_order if col in df.columns])
    if 'Start Date (Local)' in df.columns:
        df = df.sort_values('Start Date (Local)', ignore_index=True)
    return df


def build_tables(activities_dir=ACTIVITIES_DIR, zones_dir=ZONES_DIR):
    """Return two DataFrames: one for runs and one for all other activity types."""
    run_rows = []
    other_rows = []
    activity_files = [f for f in os.listdir(activities_dir) if f.endswith('.json')]

    for activity_file in activity_files:
        activity_id = os.path.splitext(activity_file)[0]

        with open(os.path.join(activities_dir, activity_file), 'r', encoding='utf-8') as f:
            activity_data = json.load(f)

        zone_path = os.path.join(zones_dir, f'{activity_id}.json')
        if os.path.exists(zone_path):
            with open(zone_path, 'r', encoding='utf-8') as f:
                zone_data = json.load(f)
        else:
            zone_data = []

        if activity_data.get('sport_type') == 'Run':
            run_rows.append(build_run_row(activity_data, zone_data))
        else:
            other_rows.append(build_other_row(activity_data, zone_data))

    return to_dataframe(run_rows, RUN_COLUMNS), to_dataframe(other_rows, OTHER_COLUMNS)


def save_table(df, name):
    csv_filename = os.path.join(OUTPUT_DIR, f'{name}.csv')
    excel_filename = os.path.join(OUTPUT_DIR, f'{name}.xlsx')

    try:
        # BOM so Excel detects UTF-8 (e.g. '×' in activity names)
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        df.to_excel(excel_filename, index=False)
    except PermissionError as e:
        print(f"Error: could not write {e.filename}. Is it open in Excel? Close it and run again.")
        return

    print(f"Files saved: {csv_filename}, {excel_filename} ({len(df)} activities)")


def main():
    runs, other = build_tables()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    save_table(runs, RUNS_NAME)
    save_table(other, OTHER_NAME)


if __name__ == '__main__':
    main()
