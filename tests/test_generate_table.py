import json

import pandas as pd

from generate_table import build_row, build_table


def run_activity(**overrides):
    activity = {
        'id': 1,
        'name': 'Morning Run',
        'sport_type': 'Run',
        'distance': 10000.0,
        'moving_time': 3000,
        'total_elevation_gain': 50.0,
        'start_date_local': '2025-05-01T07:30:00Z',
        'average_speed': 10000 / 3000,
        'average_heartrate': 150.0,
        'max_heartrate': 175.0,
        'calories': 700.0,
        'average_cadence': 85.0,
        'workout_type': 0,
    }
    activity.update(overrides)
    return activity


def write_json(path, data):
    path.write_text(json.dumps(data), encoding='utf-8')


def test_build_row_basic_fields():
    row = build_row(run_activity(), [])

    assert row['Activity ID'] == 1
    assert row['Moving Time (s)'] == '0:50:00'
    assert row['Start Date (Local)'] == '2025-05-01 07:30:00'
    assert row['Pace (min/km)'] == '5:00'
    assert row['Avg Cadence (steps/min)'] == 170.0
    assert row['Race'] == 'No'


def test_build_row_race_flag():
    assert build_row(run_activity(workout_type=1), [])['Race'] == 'Yes'


def test_build_row_missing_speed_and_cadence():
    row = build_row(run_activity(average_speed=0, average_cadence=None), [])

    assert row['Pace (min/km)'] is None
    assert row['Avg Cadence (steps/min)'] is None


def test_build_row_zones():
    zones = [
        {'type': 'heartrate', 'distribution_buckets': [{'time': t} for t in [10, 20, 30, 40, 50]]},
        {'type': 'pace', 'distribution_buckets': [{'time': t} for t in [1, 2, 3, 4, 5, 6, 7]]},
    ]
    row = build_row(run_activity(), zones)

    assert row['Heart Rate - Zone 1'] == 10
    assert row['Heart Rate - Zone 5'] == 50
    assert row['Pace - Zone 6'] == 6
    assert 'Pace - Zone 7' not in row


def test_build_table_skips_non_runs_and_handles_missing_zones(tmp_path):
    activities = tmp_path / 'activities'
    zones = tmp_path / 'zones'
    activities.mkdir()
    zones.mkdir()

    write_json(activities / '1.json', run_activity(id=1))
    write_json(activities / '2.json', run_activity(id=2, sport_type='Ride'))
    write_json(activities / '3.json', run_activity(id=3))
    write_json(zones / '1.json', [{'type': 'heartrate', 'distribution_buckets': [{'time': 99}]}])

    df = build_table(str(activities), str(zones))

    assert sorted(df['Activity ID'].tolist()) == [1, 3]
    by_id = df.set_index('Activity ID')
    assert by_id.loc[1, 'Heart Rate - Zone 1'] == 99
    assert pd.isna(by_id.loc[3, 'Heart Rate - Zone 1'])
    assert list(df.columns)[:3] == ['Activity ID', 'Name', 'Start Date (Local)']
