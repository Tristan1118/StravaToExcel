import json
import socket
import threading
import time

import pytest
import requests

import authenticate


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.text = json.dumps(data)

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


@pytest.fixture(autouse=True)
def isolated_files(tmp_path, monkeypatch):
    monkeypatch.setattr(authenticate, 'AUTH_FILE', str(tmp_path / 'auth.json'))
    monkeypatch.setattr(authenticate, 'ERROR_LOG_FILE', str(tmp_path / 'error.log'))
    # Keep a real .env from leaking into the tests
    monkeypatch.setattr(authenticate, 'load_dotenv', lambda: None)
    monkeypatch.setenv('STRAVA_CLIENT_ID', '123')
    monkeypatch.setenv('STRAVA_CLIENT_SECRET', 'secret')
    return tmp_path


def write_auth(expires_at):
    authenticate.save_json(authenticate.AUTH_FILE, {
        'access_token': 'old-token',
        'refresh_token': 'refresh',
        'expires_at': expires_at,
    })


def test_credentials_from_env():
    assert authenticate.load_client_credentials() == ('123', 'secret')


def test_missing_credentials_raise(monkeypatch):
    monkeypatch.delenv('STRAVA_CLIENT_SECRET')
    with pytest.raises(authenticate.AuthError):
        authenticate.load_client_credentials()


def test_missing_auth_file_raises():
    with pytest.raises(authenticate.AuthError, match='--login'):
        authenticate.get_access_token()


def test_valid_token_is_returned_without_request(monkeypatch):
    write_auth(time.time() + 3600 * 5)

    def fail(*args, **kwargs):
        raise AssertionError("should not request a new token")

    monkeypatch.setattr(authenticate.requests, 'post', fail)
    assert authenticate.get_access_token() == 'old-token'


def test_expired_token_is_refreshed_and_saved(monkeypatch):
    write_auth(time.time() + 60)
    sent = {}

    def fake_post(url, data):
        sent.update(data)
        return FakeResponse({'access_token': 'new-token', 'refresh_token': 'refresh2',
                             'expires_at': time.time() + 3600 * 6})

    monkeypatch.setattr(authenticate.requests, 'post', fake_post)

    assert authenticate.get_access_token() == 'new-token'
    assert sent['grant_type'] == 'refresh_token'
    assert sent['client_id'] == '123'
    assert authenticate.load_json(authenticate.AUTH_FILE)['refresh_token'] == 'refresh2'


def test_failed_refresh_raises_and_logs(monkeypatch, isolated_files):
    write_auth(time.time() - 10)
    monkeypatch.setattr(authenticate.requests, 'post',
                        lambda url, data: FakeResponse({'message': 'Bad Request'}, 400))

    with pytest.raises(authenticate.AuthError):
        authenticate.get_access_token()
    assert (isolated_files / 'error.log').exists()
    assert authenticate.load_json(authenticate.AUTH_FILE)['access_token'] == 'old-token'


def free_port():
    with socket.socket() as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]


def test_callback_server_captures_code(monkeypatch):
    port = free_port()
    monkeypatch.setattr(authenticate, 'REDIRECT_PORT', port)
    result = {}
    thread = threading.Thread(target=lambda: result.update(value=authenticate.wait_for_auth_code()))
    thread.start()
    time.sleep(0.2)

    assert requests.get(f'http://localhost:{port}/favicon.ico').status_code == 404
    response = requests.get(f'http://localhost:{port}/callback?code=abc&scope=read,activity:read_all')
    thread.join(timeout=5)

    assert response.status_code == 200
    assert result['value'] == ('abc', 'read,activity:read_all')
