import requests
import json
import time

import os

# API Key check
API_KEY = os.environ.get("LTA_ACCOUNT_KEY")
if not API_KEY:
    # Fallback to local file if exists (for local convenience, ignored by git)
    try:
        with open("api_key.txt", "r") as f:
            API_KEY = f.read().strip()
    except FileNotFoundError:
        pass

if not API_KEY:
    raise ValueError("Please set LTA_ACCOUNT_KEY environment variable or create api_key.txt")
    
BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice/"

def fetch_lta_data(endpoint):
    results = []
    seen = set()
    skip = 0
    headers = {
        'AccountKey': API_KEY,
        'accept': 'application/json'
    }
    
    while True:
        url = f"{BASE_URL}{endpoint}?$skip={skip}"
        print(f"Fetching {endpoint} (skip={skip})...")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            value = data.get('value', [])
            if not value:
                break
            
            new_records_added = 0
            for record in value:
                # Use a stable string representation for deduplication
                record_str = json.dumps(record, sort_keys=True)
                if record_str not in seen:
                    seen.add(record_str)
                    results.append(record)
                    new_records_added += 1
            
            # If no NEW records were added in this batch, we might be looping
            if new_records_added == 0:
                print(f"No new records found in batch (skip={skip}). Stopping.")
                break
                
            skip += 50
            # Small sleep to be polite to the API
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            break
            
    return results

def save_to_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} records to {filename}")

if __name__ == "__main__":
    # Download Bus Services
    print("Starting Bus Services download...")
    bus_services = fetch_lta_data("BusServices")
    save_to_json(bus_services, "bus_services.json")
    
    # Download Bus Stops
    print("\nStarting Bus Stops download...")
    bus_stops = fetch_lta_data("BusStops")
    save_to_json(bus_stops, "bus_stops.json")

    # Download Bus Routes
    print("\nStarting Bus Routes download...")
    bus_routes = fetch_lta_data("BusRoutes")
    save_to_json(bus_routes, "bus_routes.json")

    print("\nDownload complete.")
