# ----- V1.0 ----
# Copyright (C) 2026 Helskov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import pandas as pd
import requests
from sklearn.ensemble import RandomForestRegressor
import pickle
import os
import configparser
import warnings
from datetime import datetime, timedelta, timezone

# Get the exact directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'config.ini')

# Check if config file exists at the dynamic path
if not os.path.exists(config_path):
    print(f"❌ ERROR: 'config.ini' not found at {config_path}! Cannot train without database settings.")
    exit()

# Load configuration
config = configparser.ConfigParser()
config.read(config_path)

warnings.simplefilter(action='ignore', category=FutureWarning)

# =====================================================================
# INITIALIZE CONFIGURATION COMPLETED
# =====================================================================

# --- HOME ASSISTANT SETTINGS ---
HA_IP = config['HomeAssistant']['HA_IP']
HA_PORT = config['HomeAssistant'].get('HA_PORT', '8123')
HA_TOKEN = config['HomeAssistant']['HA_TOKEN']
DAYS = int(config['HomeAssistant'].get('TRAINING_DAYS', 14))

# --- SENSOR SETTINGS ---
# Build EV lists for explicit unit handling with section fallback safety
ev_sensors_w_raw = config.get('Sensors_EV', 'EV_CHARGERS_W', fallback='')
EV_SENSORS_W = [s.strip() for s in ev_sensors_w_raw.split(',') if s.strip()]

ev_sensors_kw_raw = config.get('Sensors_EV', 'EV_CHARGERS_KW', fallback='')
EV_SENSORS_KW = [s.strip() for s in ev_sensors_kw_raw.split(',') if s.strip()]

# Combined list for later use
EV_SENSORS = EV_SENSORS_W + EV_SENSORS_KW

# Core sensors
PV_SENSOR = config['Sensors_Core']['PV_POWER']
GRID_SENSOR = config['Sensors_Core']['GRID_POWER']
BATT_SENSOR = config['Sensors_Core']['BATTERY_POWER']
TEMP_SENSOR = config['Sensors_Core']['WEATHER_TEMP']

print(f"🧠 Solplanet Automation: Training Engine starting...")
print(f"⏳ Fetching last {DAYS} days of data from Home Assistant at {HA_IP}...")

def fetch_data(measurement, entity_id, days=DAYS):
    """Fetches data from Home Assistant History REST API with explicit UTC timestamp formatting."""
    import urllib.parse

    # Calculate start time in UTC and format it cleanly (Python 3.12+ compliant)
    start_utc = datetime.now(timezone.utc) - timedelta(days=days)
    start_time_str = start_utc.replace(microsecond=0).isoformat()
    encoded_start = urllib.parse.quote(start_time_str)

    # Calculate end time in UTC (Right now)
    end_utc = datetime.now(timezone.utc)
    end_time_str = end_utc.replace(microsecond=0).isoformat()
    encoded_end = urllib.parse.quote(end_time_str)

    # URL encode both timestamps and add 'end_time' parameter to override HA's 1-day default
    url = f"http://{HA_IP}:{HA_PORT}/api/history/period/{encoded_start}?end_time={encoded_end}&filter_entity_id={entity_id}&minimal_response=1"

    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "content-type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=60)

        if response.status_code != 200:
            print(f"⚠️ API Error for {entity_id}: HTTP {response.status_code} - Check your HA_TOKEN or HA_IP.")
            return pd.DataFrame()

        data = response.json()
        if not data or len(data) == 0 or len(data[0]) == 0:
            print(f"ℹ️ Connected to HA, but historical database returned 0 rows for {entity_id} over the last {days} days.")
            return pd.DataFrame()

        points = data[0]
        print(f"📥 Successfully retrieved {len(points)} raw data points from HA for {entity_id}")

        records = []
        for p in points:
            state = p.get('state')
            if state is None or state in ['unknown', 'unavailable', 'None', '']:
                continue
            try:
                val = float(state)
                # FIX: Fanger både standard og minimal-response tidsstempler
                t_str = p.get('last_updated') or p.get('last_changed')

                if not t_str:
                    continue

                records.append({'time': t_str, 'value': val})
            except ValueError:
                continue

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df['time'] = pd.to_datetime(df['time'], format='mixed', utc=True).dt.tz_convert('Europe/Copenhagen').dt.tz_localize(None)
        df.set_index('time', inplace=True)
        df.sort_index(inplace=True)

        # Drop duplicate timestamps to ensure a clean starting baseline
        df = df[~df.index.duplicated(keep='last')]

        # Resample to a clean 1-minute grid first to force perfect monotonicity
        df_min = df.resample('1min').mean()

        # Now safely forward-fill the empty gaps up to 2 hours (120 minutes) on the clean grid
        df_min_filled = df_min.ffill(limit=120).fillna(0)

        # Downsample to 1-hour averages for the ML trainer
        df_hour = df_min_filled.resample('1h').mean()
        df_hour.rename(columns={'value': entity_id}, inplace=True)
        return df_hour

    except Exception as e:
        print(f"❌ Critical exception fetching data for {entity_id}: {e}")
        return pd.DataFrame()

# --- DATA GATHERING ---
print("📥 Gathering sensor history...")
df_pv = fetch_data('W', PV_SENSOR)
df_grid = fetch_data('W', GRID_SENSOR)
df_batt = fetch_data('W', BATT_SENSOR)
df_temp = fetch_data('°C', TEMP_SENSOR)

# Gather EV data - request exact unit from InfluxDB
ev_dfs = []

# Fetch chargers in W
for s in EV_SENSORS_W:
    ev_dfs.append(fetch_data('W', s))

# Fetch chargers in kW
for s in EV_SENSORS_KW:
    ev_dfs.append(fetch_data('kW', s))

# --- DATA CLEANING & MERGING ---
# Filter out empty DataFrames from ev_dfs before merging
valid_ev_dfs = [e for e in ev_dfs if not e.empty]

# Use outer join to keep all timestamps from core sensors
df = pd.concat([df_pv, df_grid, df_batt, df_temp] + valid_ev_dfs, axis=1)

print("\n🔍 --- DIAGNOSTICS: Checking start time for each sensor ---")
for col in [PV_SENSOR, GRID_SENSOR, BATT_SENSOR, TEMP_SENSOR]:
    if col in df.columns:
        start_time = df[col].first_valid_index()
        hours_total = df[col].notna().sum()
        print(f"🔹 {col}:")
        print(f"   First data point found: {start_time}")
        print(f"   Total hours of data: {hours_total} hours\n")
print("-----------------------------------------------------------\n")

# =====================================================================
# VALIDATE DATA AND CONFIG.INI
# =====================================================================

# 1. Check if the dataframe contains any data at all
if df is None or df.empty:
    print("\n❌ ERROR: No training data found in Home Assistant history!")
    print("Please check the following:")
    print("  - Is your HA_IP and HA_PORT correct in 'config.ini'?")
    print("  - Is your HA_TOKEN valid and active?")
    print("  - Has Home Assistant recorded data for the requested period?")
    exit()

# 2. Check if all core sensors exist in the fetched database columns
core_sensors = {
    'PV_POWER': PV_SENSOR,
    'GRID_POWER': GRID_SENSOR,
    'BATTERY_POWER': BATT_SENSOR,
    'WEATHER_TEMP': TEMP_SENSOR
}

missing_sensors = []
for key, sensor_id in core_sensors.items():
    if sensor_id not in df.columns:
        missing_sensors.append(f"{key}: '{sensor_id}'")

# If any core sensors are missing, exit gracefully with clear instructions
if missing_sensors:
    print("\n❌ ERROR: Configuration Mismatch! Core sensors missing in database history.")
    print("The training engine cannot continue without these sensors:")
    for missing in missing_sensors:
        print(f"  - {missing}")
    print("\n💡 How to fix this:")
    print("1. Open 'config.ini' and check for typos under [Sensors_Core].")
    print("2. Verify in Home Assistant that these sensors are actually recording data.")
    print("3. Ensure your Home Assistant history recorder is logging these specific entities.")
    exit()

# 3. Safe to clean data now that column existence is verified
df.dropna(subset=[PV_SENSOR, GRID_SENSOR, BATT_SENSOR, TEMP_SENSOR], inplace=True)

# Fill any remaining gaps in EV columns with 0.0 so they don't break calculations
for s in EV_SENSORS:
    if s in df.columns:
        df[s] = df[s].fillna(0.0)

# =====================================================================
# DATA VALIDATION COMPLETED SUCCESSFULLY
# =====================================================================
# Calculate Naked House Load safely (Total - EVs)
df['total_ev_w'] = 0.0

# Add W chargers
for s in EV_SENSORS_W:
    if s in df.columns:
        df[s] = df[s].fillna(0)
        df['total_ev_w'] += df[s]
    else:
        print(f"⚠️ Warning: EV sensor '{s}' not found in W history. Assuming 0 W.")

# Add kW chargers multiplied by 1000
for s in EV_SENSORS_KW:
    if s in df.columns:
        df[s] = df[s].fillna(0)
        df['total_ev_w'] += df[s] * 1000.0
    else:
        print(f"⚠️ Warning: EV sensor '{s}' not found in kW history. Assuming 0 W.")

# Here the calculation runs ONLY ONCE:
df['total_load'] = df[PV_SENSOR] + df[GRID_SENSOR] + df[BATT_SENSOR]
df['naked_load'] = (df['total_load'] - df['total_ev_w']).clip(lower=0)

# Features for Machine Learning (Must be kept)
df['hour'] = df.index.hour
df['weekday'] = df.index.weekday
df['is_weekend'] = df['weekday'].apply(lambda x: 1 if x >= 5 else 0)

X = df[['hour', 'weekday', 'is_weekend', TEMP_SENSOR]]
y = df['naked_load']

print(f"🏗️ Training brain on {len(df)} hours of house history...")
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X, y)
from sklearn.metrics import mean_absolute_error, r2_score
y_pred = model.predict(X)
print(f"📊 Data Quality (R² Score): {r2_score(y, y_pred) * 100:.1f}% (Over 80% is great)")
print(f"⚖️ Average deviation (MAE): {mean_absolute_error(y, y_pred):.0f} W")
# Save the brain using absolute path
model_path = os.path.join(script_dir, 'ml_solcelle_model.pkl')
with open(model_path, 'wb') as f:
    pickle.dump(model, f)

print(f"✅ SUCCESS: 'ml_solcelle_model.pkl' created at {datetime.now().strftime('%H:%M:%S')}")
