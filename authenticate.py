import json
import time
import requests
from datetime import datetime

AUTH_FILE = 'auth.json'
CLIENT_FILE = 'client.json'
ERROR_LOG_FILE = 'error.log'
TOKEN_URL = 'https://www.strava.com/oauth/token'


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


def is_token_valid(expires_at):
    # Check if token is valid for at least 30 more minutes (1800 seconds)
    return time.time() < (expires_at - 1800)


def refresh_access_token(auth_data, client_data):
    payload = {
        'client_id': client_data['client_id'],
        'client_secret': client_data['client_secret'],
        'refresh_token': auth_data['refresh_token'],
        'grant_type': 'refresh_token'
    }

    try:
        response = requests.post(TOKEN_URL, data=payload)
        response.raise_for_status()
        new_auth_data = response.json()
        save_json(AUTH_FILE, new_auth_data)
        print("Token refreshed successfully.")
    except requests.RequestException as e:
        log_error(f"Failed to refresh token: {e}\nResponse: {response.text if 'response' in locals() else 'N/A'}")
        print("Error: Failed to refresh token. Check error.log.")


def main():
    auth_data = load_json(AUTH_FILE)
    client_data = load_json(CLIENT_FILE)

    if is_token_valid(auth_data['expires_at']):
        print("Token is still valid.")
    else:
        print("Token expired. Refreshing...")
        refresh_access_token(auth_data, client_data)


if __name__ == '__main__':
    main()
