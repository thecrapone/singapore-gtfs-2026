import csv
import json
import os
import zipfile
from datetime import datetime, timedelta

# Configuration
OUTPUT_DIR = "gtfs_output"
START_DATE = "20250101"
END_DATE = "20301231"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Helper function to write CSV
def write_csv(filename, headers, rows):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Generated {filename} with {len(rows)} rows.")

# Load Data
print("Loading data...")
with open("bus_stops.json") as f:
    bus_stops = json.load(f)
with open("bus_services.json") as f:
    bus_services = json.load(f)
with open("bus_routes.json") as f:
    bus_routes = json.load(f)
with open("rail_data.json") as f:
    rail_data = json.load(f)

# 1. agency.txt
agency_rows = [
    ["LTA", "Land Transport Authority", "https://www.lta.gov.sg", "Asia/Singapore", "en"],
    ["SBST", "SBS Transit", "https://www.sbstransit.com.sg", "Asia/Singapore", "en"],
    ["SMRT", "SMRT Corporation", "https://www.smrt.com.sg", "Asia/Singapore", "en"],
    ["TTS", "Tower Transit Singapore", "https://towertransit.sg", "Asia/Singapore", "en"],
    ["GAS", "Go-Ahead Singapore", "https://www.go-aheadsingapore.com", "Asia/Singapore", "en"]
]
write_csv("agency.txt", ["agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang"], agency_rows)

# 2. calendar.txt
# Service IDs: WD (Weekday), SAT (Saturday), SUN (Sunday)
calendar_rows = [
    ["WD", "1", "1", "1", "1", "1", "0", "0", START_DATE, END_DATE],
    ["SAT", "0", "0", "0", "0", "0", "1", "0", START_DATE, END_DATE],
    ["SUN", "0", "0", "0", "0", "0", "0", "1", START_DATE, END_DATE]
]
write_csv("calendar.txt", ["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"], calendar_rows)

# 3. stops.txt
stops_rows = []
seen_stops = set()

# Bus Stops
for stop in bus_stops:
    stop_id = stop["BusStopCode"]
    if stop_id in seen_stops:
        continue
    seen_stops.add(stop_id)
    stops_rows.append([
        stop_id,
        stop["Description"],
        stop["Latitude"],
        stop["Longitude"],
        "0", # location_type = stop
        "" # parent_station (none)
    ])

# MRT Stations (from rail_data.json)
# We need to handle multi-line stations (e.g. Dhoby Ghaut NS24/NE6/CC1).
# Strategy: Create a parent station for the interchange, and child stops for platforms or lines if detailed,
# but for simplicity, we'll treat each station code as a stop, or just one stop per station name?
# GTFS best practice for interchanges: One parent station, unrelated stops for each line if they are separate platforms.
# Given the data "station_codes": "NS10", we can use that as stop_id. If multiple, e.g. "NS24,NE6,CC1", split?
# Let's check rail_data structure again.

rail_features = rail_data["features"]
for feature in rail_features:
    props = feature["properties"]
    if props.get("stop_type") == "station":
        name = props["name"]
        coords = feature["geometry"]["coordinates"]
        codes = props.get("station_codes", "").split(",")
        
        # Punggol Coast manual patch if missing
        # (It might be missing from this dataset if it's older)
        
        # For each code, create a stop? Or one stop per station?
        # If we use one stop per station, we need a unique ID.
        # Let's use the first code as the ID, but this is risky for transfers.
        # Better: Create a stop for EACH code, so routing works on lines.
        # AND create a parent station to link them? 
        # For this MVP, let's create one stop per code.
        
        for code in codes:
            code = code.strip()
            if not code: continue
            if code in seen_stops: continue
            seen_stops.add(code)
            
            stops_rows.append([
                code,
                f"{name} {code}", # Name + Code for clarity
                coords[1], # Lat
                coords[0], # Lon
                "1", # location_type = station (actually 1 is station, 0 is stop/platform)
                # Let's make them type 0 for now so they can be used in stop_times
                # If we want to group them, we'd need a parent. 
                # Let's stick to type 0
            ])
            # Fix above: location_type 0 is stop. 
            stops_rows[-1][4] = "0"
            stops_rows[-1].append("") # parent_station


# Manual add Punggol Coast (NE18) if not present
if "NE18" not in seen_stops:
    # Approx coords for Punggol Coast
    stops_rows.append(["NE18", "Punggol Coast NE18", 1.4251, 103.9056, "0", ""])
    
write_csv("stops.txt", ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"], stops_rows)

# 4. routes.txt
routes_rows = []
# Bus Routes
operator_map = {"SBST": "SBST", "SMRT": "SMRT", "TTS": "TTS", "GAS": "GAS", "LTA": "LTA"} 

# 4b. feed_info.txt (Recommended)
feed_info_rows = [[
    "Singapore GTFS", 
    "https://github.com/thecrapone/singapore-gtfs-2025", 
    "en", 
    START_DATE, 
    END_DATE,
    "1.0",
    "https://github.com/thecrapone/singapore-gtfs-2025/issues", # feed_contact_url
    "support@example.com" # feed_contact_email (placeholder)
]]
write_csv("feed_info.txt", ["feed_publisher_name", "feed_publisher_url", "feed_lang", "feed_start_date", "feed_end_date", "feed_version", "feed_contact_url", "feed_contact_email"], feed_info_rows)

import math
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# Pre-load stop coordinates for speed checks
stop_coords = {stop["BusStopCode"]: (stop["Latitude"], stop["Longitude"]) for stop in bus_stops}
# Add manual stops logic here if needed or just handle missing keys

for service in bus_services:
    route_id = service["ServiceNo"]
    agency_id = operator_map.get(service["Operator"], "LTA")
    
    if any(r[0] == route_id for r in routes_rows):
        continue
        
    routes_rows.append([
        route_id,
        agency_id,
        route_id,
        f"Bus Service {route_id}",
        "3", # Bus
        "009645" # SBST Green-ish default, or generic. Let's use generic "333333" if unknown. Or purple for buses?
                 # LTA doesn't strictly color buses. Let's use a standard Bus Color: 007A33 (Green) or similar.
                 # Let's use 444444 (Dark Grey) as neutral.
    ])
    # Update default color above to 444444
    routes_rows[-1][5] = "444444"

# MRT Routes
# Colors must be 6-char hex
mrt_lines = [
    ("NS", "SMRT", "North-South Line", "D42E12"), # Red
    ("EW", "SMRT", "East-West Line", "009645"),   # Green
    ("NE", "SBST", "North East Line", "8F4199"),  # Purple
    ("CC", "SMRT", "Circle Line", "FA9E0D"),      # Orange
    ("DT", "SBST", "Downtown Line", "005EC4"),    # Blue
    ("TE", "SMRT", "Thomson-East Coast Line", "9D5B25"), # Brown
    ("BP", "SMRT", "Bukit Panjang LRT", "748477"), # Grey
    ("SK", "SBST", "Sengkang LRT", "748477"),      # Grey
    ("PG", "SBST", "Punggol LRT", "748477")        # Grey
]

for code, agency, name, color in mrt_lines:
    routes_rows.append([
        code, # Route ID
        agency,
        code,
        name,
        "1", # Subway
        color
    ])

write_csv("routes.txt", ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type", "route_color"], routes_rows)

# 5. trips.txt and 6. stop_times.txt
trips_rows = []
stop_times_rows = []

# BUS GENERATION
print("Generating bus trips...")
bus_services_map = {(s["ServiceNo"], s["Direction"]): s for s in bus_services}

bus_routes_grouped = {}
for r in bus_routes:
    key = (r["ServiceNo"], r["Direction"])
    if key not in bus_routes_grouped:
        bus_routes_grouped[key] = []
    bus_routes_grouped[key].append(r)

MAX_BUFFER = 100000
trips_buffer = []
stop_times_buffer = []

def flush_trips():
    with open(os.path.join(OUTPUT_DIR, "trips.txt"), 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(trips_buffer)
    trips_buffer.clear()

def flush_stop_times():
    with open(os.path.join(OUTPUT_DIR, "stop_times.txt"), 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(stop_times_buffer)
    stop_times_buffer.clear()

write_csv("trips.txt", ["route_id", "service_id", "trip_id", "trip_headsign", "direction_id"], [])
write_csv("stop_times.txt", ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"], [])

count = 0
for key, stops in bus_routes_grouped.items():
    service_no, direction = key
    route_id = service_no
    
    # Sort by sequence
    stops.sort(key=lambda x: x["StopSequence"])
    
    # Get service info
    service_info = bus_services_map.get(key)
    if not service_info:
        continue
    
    # GTFS Direction ID: 0 or 1.
    # LTA Direction: 1 or 2.
    # Map 1->0, 2->1.
    gtfs_direction_id = "0" if str(direction) == "1" else "1"

    # Process each day type
    for day_type in ["WD", "SAT", "SUN"]:
        # Extract timings
        first_bus_key = f"{day_type}_FirstBus"
        last_bus_key = f"{day_type}_LastBus"
        
        start_time_str = stops[0].get(first_bus_key, "0530")
        end_time_str = stops[0].get(last_bus_key, "2330")
        
        if not start_time_str.isdigit(): start_time_str = "0530"
        if not end_time_str.isdigit(): end_time_str = "2330"

        # Parse times (HHMM)
        start_min = int(start_time_str[:2]) * 60 + int(start_time_str[2:])
        end_min = int(end_time_str[:2]) * 60 + int(end_time_str[2:])
        if end_min < start_min: end_min += 24 * 60 
        
        # Frequency
        freq_str = service_info.get("AM_Peak_Freq", "12-15")
        if "-" in freq_str:
            try:
                l, h = map(int, freq_str.split("-"))
                freq = (l + h) / 2
            except:
                freq = 15
        else:
            freq = 15
        
        if freq <= 0:
            freq = 15 # Fallback if 0
        
        # Generate trips
        current_min = start_min
        trip_idx = 0
        
        while current_min <= end_min:
            trip_id = f"{service_no}_{direction}_{day_type}_{trip_idx}"
            trips_buffer.append([
                route_id,
                day_type,
                trip_id,
                f"Dir {direction}",
                gtfs_direction_id
            ])
            
            # Stop times
            trip_start_min = current_min
            last_arrival_min = -1.0 # For monotonicity check
            last_stop_code = None
            
            for stop in stops:
                stop_code = stop["BusStopCode"]
                # CHECK: Does this stop exist in stops.txt?
                # If not, skip it to avoid foreign key violation.
                # However, skipping a stop might break sequence continuity.
                # But it's better than invalid feed.
                # Ideally we check 'seen_stops' set.
                if stop_code not in seen_stops:
                    # Optional: Add it to stops.txt on the fly? 
                    # No, complicated now because stops.txt is closed.
                    # We just skip.
                    continue

                dist = stop.get("Distance", 0) or 0
                travel_time_min = dist * 2.4 # 25km/h approx
                arrival_min = trip_start_min + travel_time_min
                
                # Enforce Monotonicity (Time Travel Fix)
                if arrival_min <= last_arrival_min:
                    arrival_min = last_arrival_min + 0.5 # Add 30 seconds buffer
                
                # HARD SPEED CHECK: Enforce Max 80km/h
                if last_stop_code and last_stop_code in stop_coords and stop_code in stop_coords:
                    c1 = stop_coords[last_stop_code]
                    c2 = stop_coords[stop_code]
                    h_dist_km = haversine(c1[0], c1[1], c2[0], c2[1])
                    
                    # Max speed 80km/h = 1.33 km/min
                    min_time_min = h_dist_km / 1.33
                    time_diff = arrival_min - last_arrival_min
                    
                    if time_diff < min_time_min:
                        # Too fast! Bump time to meet strict physics check
                        arrival_min = last_arrival_min + min_time_min
                
                last_arrival_min = arrival_min
                last_stop_code = stop_code
                
                total_sec = int(arrival_min * 60)
                h, m, s = total_sec // 3600, (total_sec % 3600) // 60, total_sec % 60
                time_str = f"{h:02d}:{m:02d}:{s:02d}"
                
                stop_times_buffer.append([
                    trip_id,
                    time_str,
                    time_str,
                    stop_code,
                    stop["StopSequence"]
                ])
            
            current_min += freq
            trip_idx += 1
            
            if len(stop_times_buffer) > MAX_BUFFER:
                flush_stop_times()
            if len(trips_buffer) > MAX_BUFFER:
                flush_trips()
    
    count += 1
    if count % 10 == 0:
        print(f"Processed {count} routes...")

# Final flush
flush_trips()
flush_stop_times()

print("Bus trips generated.")

# MRT GENERATION
print("Generating MRT trips...")

# Hardcoded line sequences (ordered)
# Derived from official maps. 
mrt_sequences = {
    "NS": ["NS1", "NS2", "NS3", "NS4", "NS5", "NS7", "NS8", "NS9", "NS10", "NS11", "NS12", "NS13", "NS14", "NS15", "NS16", "NS17", "NS19", "NS20", "NS21", "NS22", "NS23", "NS24", "NS25", "NS26", "NS27", "NS28"],
    "EW": ["EW1", "EW2", "EW3", "EW4", "EW5", "EW6", "EW7", "EW8", "EW9", "EW10", "EW11", "EW12", "EW13", "EW14", "EW15", "EW16", "EW17", "EW18", "EW19", "EW20", "EW21", "EW22", "EW23", "EW24", "EW25", "EW26", "EW27", "EW28", "EW29", "EW30", "EW31", "EW32", "EW33"],
    "NE": ["NE1", "NE3", "NE4", "NE5", "NE6", "NE7", "NE8", "NE9", "NE10", "NE11", "NE12", "NE13", "NE14", "NE15", "NE16", "NE17", "NE18"], 
    "CC": ["CC1", "CC2", "CC3", "CC4", "CC5", "CC6", "CC7", "CC8", "CC9", "CC10", "CC11", "CC12", "CC13", "CC14", "CC15", "CC16", "CC17", "CC19", "CC20", "CC21", "CC22", "CC23", "CC24", "CC25", "CC26", "CC27", "CC28", "CC29"], 
    "DT": ["DT1", "DT2", "DT3", "DT5", "DT6", "DT7", "DT8", "DT9", "DT10", "DT11", "DT12", "DT13", "DT14", "DT15", "DT16", "DT17", "DT18", "DT19", "DT20", "DT21", "DT22", "DT23", "DT24", "DT25", "DT26", "DT27", "DT28", "DT29", "DT30", "DT31", "DT32", "DT33", "DT34", "DT35"], 
    "TE": ["TE1", "TE2", "TE3", "TE4", "TE5", "TE6", "TE7", "TE8", "TE9", "TE10", "TE11", "TE12", "TE13", "TE14", "TE15", "TE16", "TE17", "TE18", "TE19", "TE20", "TE22", "TE23", "TE24", "TE25", "TE26", "TE27", "TE28", "TE29"] 
}

# Config
mrt_start_time = 5 * 60 + 30 # 05:30
mrt_end_time = 23 * 60 + 30  # 23:30
mrt_peak_freq = 3 # mins
mrt_offpeak_freq = 6 # mins
time_per_station = 3 # mins

for line_id, sequence in mrt_sequences.items():
    
    valid_sequence = [s for s in sequence if s in seen_stops]
    
    print(f"Generating {line_id} with {len(valid_sequence)} stations.")
    if len(valid_sequence) < 2:
        print(f"Skipping {line_id}, too few stations.")
        continue

    # Directions: 0 (Forward), 1 (Backward)
    directions = [(0, valid_sequence), (1, valid_sequence[::-1])]
    
    for direction_id, stops_list in directions:
        
        # Generate trips for all days
        for day_type in ["WD", "SAT", "SUN"]:
            
            current_min = mrt_start_time
            trip_idx = 0
            
            while current_min < mrt_end_time:
                trip_id = f"{line_id}_{direction_id}_{day_type}_{trip_idx}"
                
                trips_buffer.append([
                    line_id,
                    day_type,
                    trip_id,
                    f"To {stops_list[-1]}", # Headsign
                    str(direction_id)
                ])
                
                # Stop times
                trip_start_min = current_min
                
                for seq_idx, stop_code in enumerate(stops_list):
                    arrival_min = trip_start_min + (seq_idx * time_per_station)
                    
                    total_sec = int(arrival_min * 60)
                    h, m, s = total_sec // 3600, (total_sec % 3600) // 60, total_sec % 60
                    time_str = f"{h:02d}:{m:02d}:{s:02d}"
                    
                    stop_times_buffer.append([
                        trip_id,
                        time_str,
                        time_str,
                        stop_code,
                        str(seq_idx + 1)
                    ])
                
                # Determine freq based on time of day
                is_peak = (7*60 <= current_min <= 9*60) or (17*60 <= current_min <= 20*60)
                freq = mrt_peak_freq if is_peak else mrt_offpeak_freq
                
                current_min += freq
                trip_idx += 1
                
                if len(stop_times_buffer) > MAX_BUFFER:
                    flush_stop_times()
                if len(trips_buffer) > MAX_BUFFER:
                    flush_trips()

flush_trips()
flush_stop_times()

print("GTFS Generation Complete. Zipping...")
with zipfile.ZipFile("singapore-gtfs.zip", 'w') as z:
    for filename in ["agency.txt", "calendar.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt", "feed_info.txt"]:
        z.write(os.path.join(OUTPUT_DIR, filename), arcname=filename)
print("Done.")
