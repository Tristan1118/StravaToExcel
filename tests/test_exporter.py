import json

import exporter


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def write_activity(directory, activity_id, start_date):
    path = directory / f'{activity_id}.json'
    path.write_text(json.dumps({'id': activity_id, 'start_date': start_date}), encoding='utf-8')


def test_newest_local_start_missing_or_empty_dir(tmp_path):
    assert exporter.newest_local_start(str(tmp_path / 'missing')) is None
    assert exporter.newest_local_start(str(tmp_path)) is None


def test_newest_local_start_picks_latest(tmp_path):
    write_activity(tmp_path, 1, '2025-01-01T08:00:00Z')
    write_activity(tmp_path, 2, '2025-03-15T06:30:00Z')
    write_activity(tmp_path, 3, '2024-12-31T23:59:59Z')
    (tmp_path / 'notes.txt').write_text('ignored')

    # 2025-03-15T06:30:00Z
    assert exporter.newest_local_start(str(tmp_path)) == 1742020200


def test_get_activities_passes_after_and_stops_on_empty_page(monkeypatch):
    pages = {1: [{'id': 1}, {'id': 2}], 2: [{'id': 3}], 3: []}
    calls = []

    def fake_request(method, url, token, params):
        calls.append(params)
        return FakeResponse(pages[params['page']])

    monkeypatch.setattr(exporter, 'strava_request', fake_request)

    ids = [a['id'] for a in exporter.get_activities('token', after=1742020200)]

    assert ids == [1, 2, 3]
    assert len(calls) == 3
    assert all(c['after'] == 1742020200 for c in calls)


def test_get_activities_without_after(monkeypatch):
    calls = []

    def fake_request(method, url, token, params):
        calls.append(params)
        return FakeResponse([])

    monkeypatch.setattr(exporter, 'strava_request', fake_request)

    assert list(exporter.get_activities('token')) == []
    assert 'after' not in calls[0]
