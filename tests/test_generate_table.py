import json

import pandas as pd

import generate_table
from generate_table import build_other_row, build_run_row, build_tables


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
    row = build_run_row(run_activity(), [])

    assert row['Activity ID'] == 1
    assert row['Moving Time (s)'] == '0:50:00'
    assert row['Start Date (Local)'] == '2025-05-01 07:30:00'
    assert row['Pace (min/km)'] == '5:00'
    assert row['Avg Cadence (steps/min)'] == 170.0
    assert row['Race'] == 'No'


def test_build_row_race_flag():
    assert build_run_row(run_activity(workout_type=1), [])['Race'] == 'Yes'


def test_build_row_missing_speed_and_cadence():
    row = build_run_row(run_activity(average_speed=0, average_cadence=None), [])

    assert row['Pace (min/km)'] is None
    assert row['Avg Cadence (steps/min)'] is None


def test_build_row_zones():
    zones = [
        {'type': 'heartrate', 'distribution_buckets': [{'time': t} for t in [10, 20, 30, 40, 50]]},
        {'type': 'pace', 'distribution_buckets': [{'time': t} for t in [1, 2, 3, 4, 5, 6, 7]]},
    ]
    row = build_run_row(run_activity(), zones)

    assert row['Heart Rate - Zone 1'] == 10
    assert row['Heart Rate - Zone 5'] == 50
    assert row['Pace - Zone 6'] == 6
    assert 'Pace - Zone 7' not in row


def test_build_other_row_ride():
    ride = run_activity(sport_type='Ride', name='Commute', average_speed=5.0, average_watts=180.0)
    zones = [
        {'type': 'heartrate', 'distribution_buckets': [{'time': 60}, {'time': 120}]},
        {'type': 'power', 'distribution_buckets': [{'time': 5}]},
    ]
    row = build_other_row(ride, zones)

    assert row['Sport Type'] == 'Ride'
    assert row['Avg Speed (km/h)'] == 18.0
    assert row['Avg Watts'] == 180.0
    assert row['Heart Rate - Zone 2'] == 120
    assert 'Pace (min/km)' not in row


def test_build_other_row_without_gps():
    workout = run_activity(sport_type='WeightTraining', distance=0.0, total_elevation_gain=0,
                           average_speed=0.0)
    row = build_other_row(workout, [])

    assert row['Distance (m)'] is None
    assert row['Elevation Gain (m)'] is None
    assert row['Avg Speed (km/h)'] is None


def test_build_tables_splits_runs_and_other(tmp_path):
    activities = tmp_path / 'activities'
    zones = tmp_path / 'zones'
    activities.mkdir()
    zones.mkdir()

    write_json(activities / '1.json', run_activity(id=1, start_date_local='2025-05-03T07:00:00Z'))
    write_json(activities / '2.json', run_activity(id=2, sport_type='Ride'))
    write_json(activities / '3.json', run_activity(id=3, start_date_local='2025-05-02T07:00:00Z'))
    write_json(activities / '4.json', run_activity(id=4, sport_type='Yoga', distance=0.0))
    write_json(zones / '1.json', [{'type': 'heartrate', 'distribution_buckets': [{'time': 99}]}])

    runs, other = build_tables(str(activities), str(zones))

    # Sorted by start date
    assert runs['Activity ID'].tolist() == [3, 1]
    by_id = runs.set_index('Activity ID')
    assert by_id.loc[1, 'Heart Rate - Zone 1'] == 99
    assert pd.isna(by_id.loc[3, 'Heart Rate - Zone 1'])
    assert list(runs.columns)[:3] == ['Activity ID', 'Name', 'Start Date (Local)']

    assert sorted(other['Activity ID'].tolist()) == [2, 4]
    assert sorted(other['Sport Type'].tolist()) == ['Ride', 'Yoga']
    assert 'Pace (min/km)' not in other.columns


def test_save_table_writes_csv_with_bom(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_table, 'OUTPUT_DIR', str(tmp_path))
    df = pd.DataFrame([{'Activity ID': 1, 'Name': 'Tempo 2×3000'}])

    generate_table.save_table(df, 'test')

    raw = (tmp_path / 'test.csv').read_bytes()
    assert raw.startswith(b'\xef\xbb\xbf')
    assert 'Tempo 2×3000' in raw.decode('utf-8-sig')
    assert (tmp_path / 'test.xlsx').exists()
