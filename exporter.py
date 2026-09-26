import os
import sys
import time
import argparse
import requests
import json
from datetime import datetime

import authenticate

BASE_URL = "https://www.strava.com/api/v3"
ACTIVITIES_LIST_ENDPOINT = f"{BASE_URL}/athlete/activities"
ACTIVITY_DETAILS_ENDPOINT = f"{BASE_URL}/activities"
ACTIVITY_ZONES_ENDPOINT = BASE_URL + "/activities/{}/zones"

LAST_REQUEST_TIME = 0

def strava_request(method, url, token, **kwargs):
    global LAST_REQUEST_TIME
    elapsed = time.time() - LAST_REQUEST_TIME
    wait_time = 9.0 - elapsed
    if wait_time > 0:
        time.sleep(wait_time)

    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"

    response = requests.request(method, url, headers=headers, **kwargs)
    LAST_REQUEST_TIME = time.time()

    response.raise_for_status()
    return response

def get_activities(token, after=None, per_page=100):
    page = 1
    while True:
        params = {"page": page, "per_page": per_page}
        if after is not None:
            params["after"] = after
        response = strava_request("GET", ACTIVITIES_LIST_ENDPOINT, token, params=params)
        activities = response.json()
        if not activities:
            break
        yield from activities
        page += 1

def fetch_activity_detail(activity_id, token):
    url = f"{ACTIVITY_DETAILS_ENDPOINT}/{activity_id}"
    response = strava_request("GET", url, token)
    return response.json()

def fetch_activity_zones(activity_id, token):
    url = ACTIVITY_ZONES_ENDPOINT.format(activity_id)
    response = strava_request("GET", url, token)
    return response.json()

def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def save_activity(activity_data, output_dir="activities"):
    activity_id = activity_data["id"]
    filepath = os.path.join(output_dir, f"{activity_id}.json")
    save_json(activity_data, filepath)
    print(f"Saved activity {activity_id} to {filepath}")

def save_zones(zones_data, activity_id, output_dir="zones"):
    filepath = os.path.join(output_dir, f"{activity_id}.json")
    save_json(zones_data, filepath)
    print(f"Saved zones for activity {activity_id} to {filepath}")

def activity_exists(activity_id, output_dir="activities"):
    return os.path.exists(os.path.join(output_dir, f"{activity_id}.json"))

def zones_exist(activity_id, output_dir="zones"):
    return os.path.exists(os.path.join(output_dir, f"{activity_id}.json"))

def newest_local_start(activities_dir="activities"):
    """Return the start time (epoch seconds) of the newest downloaded activity, or None."""
    if not os.path.isdir(activities_dir):
        return None

    newest = None
    for filename in os.listdir(activities_dir):
        if not filename.endswith(".json"):
            continue
        with open(os.path.join(activities_dir, filename), "r", encoding="utf-8") as f:
            start_date = json.load(f).get("start_date")
        if not start_date:
            continue
        # Strava uses a trailing "Z" for UTC
        timestamp = int(datetime.fromisoformat(start_date.replace("Z", "+00:00")).timestamp())
        if newest is None or timestamp > newest:
            newest = timestamp
    return newest


def main():
    parser = argparse.ArgumentParser(description="Download Strava activities and zones as JSON.")
    parser.add_argument("--all", action="store_true",
                        help="List all activities instead of only those newer than the newest local one. "
                             "Existing files are still skipped, so this only fills gaps.")
    args = parser.parse_args()

    try:
        token = authenticate.get_access_token()
    except authenticate.AuthError as e:
        print(f"Error: {e}")
        sys.exit(1)

    after = None if args.all else newest_local_start()
    if after is None:
        print("Listing all activities...")
    else:
        print(f"Listing activities after {datetime.fromtimestamp(after)}...")

    for activity in get_activities(token, after=after):
        activity_id = activity["id"]

        # Download and save full activity details
        if activity_exists(activity_id):
            print(f"Skipping existing activity {activity_id}")
        else:
            try:
                detail = fetch_activity_detail(activity_id, token)
                save_activity(detail)
            except requests.HTTPError as e:
                print(f"Failed to fetch activity {activity_id}: {e}")

        # Download and save zones
        if zones_exist(activity_id):
            print(f"Skipping existing zones for activity {activity_id}")
        else:
            try:
                zones = fetch_activity_zones(activity_id, token)
                save_zones(zones, activity_id)
            except requests.HTTPError as e:
                print(f"Failed to fetch zones for activity {activity_id}: {e}")

if __name__ == "__main__":
    main()
