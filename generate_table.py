import os
import json
import pandas as pd
from datetime import datetime, timedelta

ACTIVITIES_DIR = './activities'
ZONES_DIR = './zones'
OUTPUT_DIR = './output'
OUTPUT_NAME = 'strava_summary'

COLUMN_ORDER = [
    'Activity ID', 'Name', 'Start Date (Local)', 'Distance (m)', 'Moving Time (s)',
    'Elevation Gain (m)', 'Pace (min/km)', 'Avg Heart Rate', 'Max Heart Rate', 'Avg Cadence (steps/min)', 'Calories', 'Race'
] + [f'Heart Rate - Zone {i}' for i in range(1, 6)] + [f'Pace - Zone {i}' for i in range(1, 7)]


def build_row(activity_data, zone_data):
    row = {}

    # Basic fields
    row['Activity ID'] = activity_data.get('id')
    row['Name'] = activity_data.get('name')
    row['Distance (m)'] = activity_data.get('distance')
    row['Moving Time (s)'] = str(timedelta(seconds=activity_data.get('moving_time', 0)))
    row['Elevation Gain (m)'] = activity_data.get('total_elevation_gain')

    # Format start date local
    start_date_local = activity_data.get('start_date_local')
    if start_date_local:
        row['Start Date (Local)'] = datetime.fromisoformat(start_date_local).strftime('%Y-%m-%d %H:%M:%S')
    else:
        row['Start Date (Local)'] = None

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


def build_table(activities_dir=ACTIVITIES_DIR, zones_dir=ZONES_DIR):
    rows = []
    activity_files = [f for f in os.listdir(activities_dir) if f.endswith('.json')]

    for activity_file in activity_files:
        activity_id = os.path.splitext(activity_file)[0]

        with open(os.path.join(activities_dir, activity_file), 'r') as f:
            activity_data = json.load(f)

        if activity_data.get('sport_type') != 'Run':
            continue

        zone_path = os.path.join(zones_dir, f'{activity_id}.json')
        if os.path.exists(zone_path):
            with open(zone_path, 'r') as f:
                zone_data = json.load(f)
        else:
            zone_data = []

        rows.append(build_row(activity_data, zone_data))

    df = pd.DataFrame(rows)
    return df.reindex(columns=[col for col in COLUMN_ORDER if col in df.columns])


def main():
    df = build_table()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_filename = os.path.join(OUTPUT_DIR, f'{OUTPUT_NAME}.csv')
    excel_filename = os.path.join(OUTPUT_DIR, f'{OUTPUT_NAME}.xlsx')

    try:
        df.to_csv(csv_filename, index=False)
        df.to_excel(excel_filename, index=False)
    except PermissionError as e:
        print(f"Error: could not write {e.filename}. Is it open in Excel? Close it and run again.")
        return

    print(f"Files saved: {csv_filename}, {excel_filename} ({len(df)} runs)")


if __name__ == '__main__':
    main()
