import os
import json
import time
import argparse
import webbrowser
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from dotenv import load_dotenv

AUTH_FILE = 'auth.json'
ERROR_LOG_FILE = 'error.log'
TOKEN_URL = 'https://www.strava.com/oauth/token'
AUTHORIZE_URL = 'https://www.strava.com/oauth/authorize'
REDIRECT_PORT = 8765
REDIRECT_URI = f'http://localhost:{REDIRECT_PORT}/callback'
SCOPE = 'read,activity:read_all'


class AuthError(Exception):
    pass


def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)


def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def log_error(message):
    timestamp = datetime.now().isoformat()
    with open(ERROR_LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")


def load_client_credentials():
    load_dotenv()
    client_id = os.environ.get('STRAVA_CLIENT_ID')
    client_secret = os.environ.get('STRAVA_CLIENT_SECRET')
    if not client_id or not client_secret:
        raise AuthError(
            "STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET must be set in the environment or in a .env file."
        )
    return client_id, client_secret


def is_token_valid(expires_at):
    # Check if token is valid for at least 30 more minutes (1800 seconds)
    return time.time() < (expires_at - 1800)


def exchange_token(payload):
    response = None
    try:
        response = requests.post(TOKEN_URL, data=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        log_error(f"Token request failed: {e}\nResponse: {response.text if response is not None else 'N/A'}")
        raise AuthError("Token request to Strava failed. Check error.log.") from e

    auth_data = response.json()
    save_json(AUTH_FILE, auth_data)
    return auth_data


def refresh_access_token(auth_data):
    client_id, client_secret = load_client_credentials()
    return exchange_token({
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': auth_data['refresh_token'],
        'grant_type': 'refresh_token',
    })


def get_access_token():
    """Return a valid access token, refreshing it first if it is about to expire."""
    if not os.path.exists(AUTH_FILE):
        raise AuthError(f"{AUTH_FILE} not found. Run 'uv run authenticate.py --login' first.")

    auth_data = load_json(AUTH_FILE)
    if not is_token_valid(auth_data['expires_at']):
        print("Token expired. Refreshing...")
        auth_data = refresh_access_token(auth_data)
        print("Token refreshed successfully.")
    return auth_data['access_token']


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        if 'code' in params:
            self.server.auth_code = params['code'][0]
            self.server.granted_scope = params.get('scope', [''])[0]
            message = "Authorization successful. You can close this window."
        elif 'error' in params:
            self.server.auth_error = params['error'][0]
            message = f"Authorization failed: {self.server.auth_error}"
        else:
            # e.g. a favicon request
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))

    def log_message(self, format, *args):
        pass


def wait_for_auth_code():
    server = HTTPServer(('localhost', REDIRECT_PORT), CallbackHandler)
    server.auth_code = None
    server.auth_error = None
    server.granted_scope = ''
    try:
        while server.auth_code is None and server.auth_error is None:
            server.handle_request()
    finally:
        server.server_close()

    if server.auth_error:
        raise AuthError(f"Strava authorization failed: {server.auth_error}")
    return server.auth_code, server.granted_scope


def login():
    client_id, client_secret = load_client_credentials()
    url = AUTHORIZE_URL + '?' + urlencode({
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'approval_prompt': 'auto',
        'scope': SCOPE,
    })

    print("Opening Strava in your browser to authorize access...")
    print(f"If it does not open, visit:\n{url}")
    webbrowser.open(url)

    code, granted_scope = wait_for_auth_code()
    if 'activity:read_all' not in granted_scope:
        print("Warning: 'activity:read_all' was not granted, so private activities will be missing.")

    exchange_token({
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
    })
    print(f"Login successful. Tokens saved to {AUTH_FILE}.")


def main():
    parser = argparse.ArgumentParser(description="Authenticate with Strava.")
    parser.add_argument('--login', action='store_true',
                        help="Authorize this app in the browser and save new tokens.")
    args = parser.parse_args()

    try:
        if args.login:
            login()
        else:
            get_access_token()
            print("Token is valid.")
    except AuthError as e:
        print(f"Error: {e}")
        raise SystemExit(1)


if __name__ == '__main__':
    main()
