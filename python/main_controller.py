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

__version__ = "1.1.0"
import time
import requests
from datetime import datetime, timedelta
import pandas as pd
import math
import pickle
import csv
import os
import configparser
import json

# =====================================================================
# INITIALIZATION & CONFIGURATION
# =====================================================================
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'config.ini')

if not os.path.exists(config_path):
    print(f"❌ ERROR: 'config.ini' not found at {config_path}!")
    exit()

config = configparser.ConfigParser()
config.read(config_path)

# --- LANGUAGE & REGIONAL SETTINGS ---
try:
    LANG = config['General'].get('LANGUAGE', 'DA').upper()
    CURRENCY = config['General'].get('CURRENCY', 'kr')
    VAT_RATE = float(config['General'].get('VAT_RATE', '1.25'))
except (KeyError, ValueError):
    LANG = 'DA'
    CURRENCY = 'kr'
    VAT_RATE = 1.25

MESSAGES = {
    "DA": {
        "plan_down_to": " (Ned til {soc}%)",
        "start": "🚀 Starter Intelligent Solcellestyring (Hjerne & Planlægger)...",
        "log_path": "📂 Logfilen gemmes her: {path}",
        "wake": "🔄 VÅGNER OG STARTER BEREGNING: {time}",
        "export_stop": "🛑 Eksport Stop: Salgspris for lav",
        "export_stop_limit": "🛑 Eksport Stop: Salgspris for lav (< {limit} kr)",
        "backup_mode": "🔵 Backup Mode: Holder batteri klar",
        "smart_sell_morning": "☀️ Grøn Morgen-Salg: Profit dækker slitage. Sælger ned til {soc}%",
        "smart_sell_evening": "🟢 Grøn Aften-Salg: Profit dækker slitage. Sælger ned til {soc}%",
        "smart_charge_night": "🔋 Smart-Lader i nat ({w}W) - Prisforskel dækker slitage!",
        "tarif_buster": "🔋 Tarif-Buster: Lader op før aften-spidsen ({w}W)!",
        "sol_throttle": "🌤️ Sol-Throttling: Sælger nu ({pris:.2f} kr) før prisdyk ({senere:.2f} kr)",
        "normal_steady": "🚀 Normal Drift: Stabil pris senere. Fyld batteri.",
        "normal_busy": "🚀 Normal Drift: Travlt med at fylde batteri. Dropper throttle.",
        "normal_low_price": "🚀 Normal Drift: Lav pris nu ({pris:.2f} kr). Sikrer batteri.",
        "normal_default": "Normal drift (Self-consumption)",
        "profit_arbitrage": "🔴 Aggressiv Arbitrage: Sælger ned til {soc}%",
        "profit_charge": "🔴 Smart-Lader lige nu! (Billig time)",
        "test_0w": "⚙️ TEST AKTIV: Opladning tvunget til 0W (AC Clipping Test)",
        "ev_shield_simple": "🛡️ Elbil Skjold (Simpel): Forbrug > {threshold}W. Batteri låst (0W)",
        "ev_shield_advanced": "🛡️ Elbil Skjold (Avanceret): Batteri dækker kun hus ({w}W)",
        "tvangsladning": "⚠️ TVANGSLADNING: Købspris er under din grænse ({pris:.2f} kr)! Fylder batteriet NU.",
        "pre_dump": "💸 PRE-DUMP: Tømmer batteri nu. Forbereder tvangsladning kl. {tid}.",
        "debug_status": "\n🔎 --- DEBUG: AKTUEL STATUS LIGE NU ---",
        "debug_temp_soc_prof": "🌡️ Temperatur: {temp:.1f}°C | 🔋 SOC: {soc:.1f}% | ⚙️ Profil: {profil}",
        "debug_prices": "💰 Pris KØB nu: {k:.2f} kr | Pris SÆLG nu: {s:.2f} kr",
        "debug_batt_info": "🔋 Batteri Info: {cap:.1f}kWh | Udregnet Slitage: {deg:.2f} kr/kWh",
        "debug_raw_measurements": "⚡ Rå Målinger  -> Sol: {sol:.0f}W | P1 Net: {p1:.0f}W | Batteri: {batt:.0f}W",
        "debug_naked_house": "🏠 NØGENT HUS  -> Beregnet ægte forbrug lige nu: {house:.0f}W",
        "action_sent": "\n📡 --- HOVED-HANDLING SENDT TIL INVERTER: {handling} ---",
        "forecast_header": "\n🔮 --- DEBUG: KRYSTALKUGLE FOR DE NÆSTE 24 TIMER ---",
        "sleep": "💤 Går i dvale (Beregner fuld AI-strategi igen om 3 minutter)...",
        "err_model": "❌ KRITISK FEJL: Kunne ikke finde 'ml_solcelle_model.pkl'. Har du kørt trænings-scriptet?",
        "err_model_load": "❌ FEJL ved indlæsning af model: {e}",
        "csv_trimming": "🧹 Logfil er over 50MB! Trimmer gamle data...",
        "csv_trimmed": "✅ Logfil trimmet med succes.",
        "csv_err": "⚠️ Kunne ikke trimme CSV fil: {e}",
        "plan_charge": "⚡ Oplader (Billig time)",
        "plan_profit": "🔴 Profit Salg: +{profit:.2f}kr",
        "plan_morning": "☀️ Morgen Salg",
        "plan_evening": "🟢 Aften Salg",
        "plan_stop": "🛑 Eksport Stop",
        "plan_export": "☀️ Sol dækker & Eksport",
        "plan_normal": "🚀 Normal Drift",
        "plan_throttle": "🌤️ Sol-Throttling (+{w}W)",
        "plan_sun_charge": "☀️ Sol lader batteri",
        "plan_batt_cover": "🔋 Batteri dækker ({w}W)",
        "plan_grid_cover": "🔌 Net dækker ({w}W)",
        "no_history": "Ingen historik fundet for denne time.",
        "err_history": "⚠️ Fejl ved læsning af CSV",
        "mem_update": "🧠 BMS-Hukommelse opdateret: [{temp}][{soc}] max opladning er nu {w}W",
        "mem_err": "⚠️ Kunne ikke gemme batteri-erfaring: {e}"
    },
    "EN": {
        "plan_down_to": " (Down to {soc}%)",
        "start": "🚀 Starting Solplanet Automation (Brain & Planner)...",
        "log_path": "📂 Log file saved at: {path}",
        "wake": "🔄 WAKING UP & CALCULATING: {time}",
        "export_stop": "🛑 Export Stop: Sell price too low",
        "export_stop_limit": "🛑 Export Stop: Sell price too low (< {limit})",
        "backup_mode": "🔵 Backup Mode: Keeping battery ready",
        "smart_sell_morning": "☀️ Smart Morning Sell: Profit covers degradation. Selling to {soc}%",
        "smart_sell_evening": "🟢 Smart Evening Sell: Profit covers degradation. Selling to {soc}%",
        "smart_charge_night": "🔋 Smart Charging tonight ({w}W) - Margin covers degradation!",
        "tarif_buster": "🔋 Peak-Buster: Pre-charging before evening peak ({w}W)!",
        "sol_throttle": "🌤️ Solar-Throttling: Selling now ({pris:.2f}) before price drops ({senere:.2f})",
        "normal_steady": "🚀 Normal Ops: Stable future price. Filling battery.",
        "normal_busy": "🚀 Normal Ops: Busy filling battery. Skipping throttle.",
        "normal_low_price": "🚀 Normal Ops: Low price now ({pris:.2f}). Securing battery.",
        "normal_default": "Normal Operation (Self-consumption)",
        "profit_arbitrage": "🔴 Aggressive Arbitrage: Discharging to {soc}%",
        "profit_charge": "🔴 Smart-Charge Active! (Cheap hour)",
        "test_0w": "⚙️ TEST ACTIVE: Charging forced to 0W (AC Clipping Test)",
        "ev_shield_simple": "🛡️ EV Shield (Simple): Load > {threshold}W. Battery locked (0W)",
        "ev_shield_advanced": "🛡️ EV Shield (Advanced): Battery covers house load only ({w}W)",
        "tvangsladning": "⚠️ FORCED CHARGE: Buy price is below your limit ({pris:.2f})! Charging NOW.",
        "pre_dump": "💸 PRE-DUMP: Selling battery now to prepare for negative price at {tid}.",
        "debug_status": "\n🔎 --- DEBUG: CURRENT STATUS ---",
        "debug_temp_soc_prof": "🌡️ Temperature: {temp:.1f}°C | 🔋 SOC: {soc:.1f}% | ⚙️ Profile: {profil}",
        "debug_prices": "💰 BUY Price now: {k:.2f} | SELL Price now: {s:.2f}",
        "debug_batt_info": "🔋 Battery Info: {cap:.1f}kWh | Calc. Degradation: {deg:.2f}/kWh",
        "debug_raw_measurements": "⚡ Raw Sensors   -> Solar: {sol:.0f}W | P1 Grid: {p1:.0f}W | Battery: {batt:.0f}W",
        "debug_naked_house": "🏠 NAKED HOUSE   -> Calc. True Consumption Now: {house:.0f}W",
        "action_sent": "\n📡 --- MAIN ACTION SENT TO INVERTER: {handling} ---",
        "forecast_header": "\n🔮 --- DEBUG: CRYSTAL BALL FOR NEXT 24 HOURS ---",
        "sleep": "💤 Entering deep sleep (Recalculating AI strategy in 3 minutes)...",
        "err_model": "❌ CRITICAL ERROR: Could not find 'ml_solcelle_model.pkl'. Did you run the training script?",
        "err_model_load": "❌ ERROR loading model: {e}",
        "csv_trimming": "🧹 Log file over 50MB! Trimming old data...",
        "csv_trimmed": "✅ Log file trimmed successfully.",
        "csv_err": "⚠️ Could not trim CSV file: {e}",
        "plan_charge": "⚡ Charging (Cheap hour)",
        "plan_profit": "🔴 Profit Sale: +{profit:.2f}",
        "plan_morning": "☀️ Morning Sale",
        "plan_evening": "🟢 Evening Sale",
        "plan_stop": "🛑 Export Stopped",
        "plan_export": "☀️ Solar covers & Exports",
        "plan_normal": "🚀 Normal Ops",
        "plan_throttle": "🌤️ Sol-Throttling (+{w}W)",
        "plan_sun_charge": "☀️ Solar charging batt",
        "plan_batt_cover": "🔋 Battery covers ({w}W)",
        "plan_grid_cover": "🔌 Grid covers ({w}W)",
        "no_history": "No history found for this hour.",
        "err_history": "⚠️ Error reading CSV",
        "mem_update": "🧠 BMS-Memory updated: [{temp}][{soc}] max charge is now {w}W",
        "mem_err": "⚠️ Could not save battery experience: {e}"
    }
}

# Automatically patch local currency symbol into the message strings
for lang_key in MESSAGES:
    for msg_key in MESSAGES[lang_key]:
        if isinstance(MESSAGES[lang_key][msg_key], str):
            MESSAGES[lang_key][msg_key] = MESSAGES[lang_key][msg_key].replace('kr', CURRENCY)

def get_msg(key, **kwargs):
    text = MESSAGES.get(LANG, MESSAGES["EN"]).get(key, key)
    return text.format(**kwargs)

# --- HOME ASSISTANT CREDENTIALS ---
HA_IP = config['HomeAssistant']['HA_IP']
HA_PORT = config['HomeAssistant'].get('HA_PORT', '8123')
HA_TOKEN = config['HomeAssistant']['HA_TOKEN']
HA_URL = f"http://{HA_IP}:{HA_PORT}/api/states/sensor.solplanet_automation_plan"

# --- HARDWARE LIMITS ---
MAX_CHARGE_W = int(config['Hardware'].get('MAX_CHARGE_W', 10000))
MAX_DISCHARGE_W = int(config['Hardware'].get('MAX_DISCHARGE_W', 10000))

# --- SENSOR NAMES (Read from config) ---
c_sens = config['Sensors_Core']
SENSOR_SOC = c_sens.get('BATTERY_SOC', '')
SENSOR_PRIS_NU_EX = c_sens.get('PRICE_SELL', '')
SENSOR_PRIS_NU_INKL = c_sens.get('PRICE_BUY', '')
SENSOR_PRIS_TOMORROW_INKL = c_sens.get('PRICE_BUY_TOMORROW', '')
SENSOR_VEJR = c_sens.get('WEATHER_ENTITY', '')
SENSOR_UDE_TEMP = c_sens.get('WEATHER_TEMP', '')
SENSOR_PV = c_sens.get('PV_POWER', '')
SENSOR_P1 = c_sens.get('GRID_POWER', '')
SENSOR_BATT_PWR = c_sens.get('BATTERY_POWER', '')
SENSOR_INVERTER_MIN_SOC = c_sens.get('INVERTER_MIN_SOC', '')
SENSOR_PRIS_TOMORROW_EX = c_sens.get('PRICE_SELL_TOMORROW', '')

# Solar Forecasts
SENSOR_SOL_PRIMARY = c_sens.get('SOLAR_FORECAST_PRIMARY', '')
raw_forecasts_str = c_sens.get('RAW_FORECASTS', '')
RAW_FORECASTS = [s.strip() for s in raw_forecasts_str.split(',') if s.strip()]

# Electric Vehicles
ev_sensors_w_raw = config['Sensors_EV'].get('EV_CHARGERS_W', '')
EV_SENSORS_W = [s.strip() for s in ev_sensors_w_raw.split(',') if s.strip()]

ev_sensors_kw_raw = config['Sensors_EV'].get('EV_CHARGERS_KW', '')
EV_SENSORS_KW = [s.strip() for s in ev_sensors_kw_raw.split(',') if s.strip()]

EV_SENSORS = EV_SENSORS_W + EV_SENSORS_KW
ev_status_raw = config['Sensors_EV'].get('EV_STATUS_SENSORS', '')
EV_STATUS_SENSORS = [s.strip() for s in ev_status_raw.split(',') if s.strip()]

# UI Helpers
SENSOR_PROFIL = "input_select.solcelle_profil"
SENSOR_MIN_SOC = "input_number.batteri_min_soc"
SENSOR_SOL_FAKTOR_BOX = "input_number.sol_faktor_threshold"
SENSOR_MIN_EKSPORT = "input_number.min_eksport_pris"
SENSOR_THROTTLE_AGGRESSION = "input_number.sol_throttle_aggressivitet"
SENSOR_SOL_LAAS_MIN_SOC = "input_number.sol_laas_min_soc"
SENSOR_ROED_PROFIT = "input_number.roed_profit_margin"
SENSOR_GROEN_MIN_SALG = "input_number.groen_min_salgspris"
SENSOR_EV_MODE = "input_select.elbil_skjold_mode"
SENSOR_EV_THRESHOLD = "input_number.elbil_skjold_simpel_graense"
SENSOR_TVANGSLADNING = "input_number.tvangsladning_ved_negativ_pris"
SENSOR_SALGS_BUFFER = "input_number.batteri_salgs_buffer"
SENSOR_THROTTLE_PRIS_DYK = "input_number.sol_throttle_pris_dyk"

# --- LOGGING & MEMORY CONFIGURATION ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(project_root, "ai_solcelle_historik.csv")
BATTERY_EXP_FILE = os.path.join(project_root, 'battery_experience.json')
PROFIT_FILE = os.path.join(project_root, 'ai_profit.json')
ROLLING_LOG_FILE = os.path.join(project_root, 'ai_rolling_48h.json')
WEATHER_STATE_FILE = os.path.join(project_root, 'ai_weather_backup_state.json')

def load_rolling_log():
    if os.path.exists(ROLLING_LOG_FILE):
        try:
            with open(ROLLING_LOG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and "history" in data and "planned_schedule" in data:
                    return data
        except Exception as e:
            print(f"⚠️ Fejl ved indlæsning af {ROLLING_LOG_FILE}: {e}")
    return {"planned_schedule": {}, "history": {}}

def save_rolling_log(data):
    try:
        with open(ROLLING_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Fejl ved gemning af {ROLLING_LOG_FILE}: {e}")

def backfill_rolling_log_from_csv(rolling_data, now):
    if not os.path.exists(LOG_FILE):
        return rolling_data
    try:
        df = pd.read_csv(LOG_FILE)
        if df.empty or 'timestamp' not in df.columns:
            return rolling_data
        df['dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['dt'])
        cutoff = now - timedelta(hours=48)
        recent_df = df[df['dt'] >= cutoff].copy()
        if recent_df.empty:
            return rolling_data
        
        recent_df['hour_key'] = recent_df['dt'].dt.strftime('%Y-%m-%d %H')
        grouped = recent_df.groupby('hour_key').last().reset_index()
        
        for _, row in grouped.iterrows():
            hk = str(row['hour_key'])
            if hk not in rolling_data["history"]:
                rolling_data["history"][hk] = {
                    "hour_key": hk,
                    "timestamp": str(row['timestamp']),
                    "pris_koeb_inkl_moms": round(float(row.get('pris_koeb_inkl_moms', 0.0)), 2),
                    "pris_salg_ex_moms": round(float(row.get('pris_salg_ex_moms', 0.0)), 2),
                    "batteri_soc": round(float(row.get('batteri_soc', 0.0)), 1),
                    "sol_w": int(row.get('pv_produktion_nu_w', row.get('sol_prognose_nu_w', 0.0))),
                    "forbrug_w": int(row.get('hus_forbrug_nu_w', 0.0)),
                    "action_id": int(row.get('action_id', 1)),
                    "target_mode": str(row.get('target_mode', 'Self-consumption')),
                    "target_charge_w": int(row.get('target_charge_w', 0)),
                    "beslutning_tekst": str(row.get('beslutning_tekst', '')),
                    "tidligere_planlagt": "Ukendt (før opdatering)"
                }
    except Exception as e:
        print(f"⚠️ Kunne ikke backfille historik fra CSV: {e}")
    return rolling_data

def load_ai_profit():
    if os.path.exists(PROFIT_FILE):
        try:
            with open(PROFIT_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"today": 0.0, "total": 0.0, "date": datetime.now().strftime("%Y-%m-%d")}

def save_ai_profit(data):
    try:
        with open(PROFIT_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except: pass

def get_battery_experience(nominal_cap):
    if os.path.exists(BATTERY_EXP_FILE):
        try:
            with open(BATTERY_EXP_FILE, 'r') as f:
                return json.load(f)
        except: pass

    default_exp = {
        "learned_capacity": nominal_cap,
        "temp_capacity_multipliers": {
            "temp_over_10": 1.0,
            "temp_0_to_10": 0.95,
            "temp_under_0": 0.85
        },
        "max_charge_rate": {
            "temp_over_10": {"soc_0_to_90": MAX_CHARGE_W, "soc_90_to_100": int(MAX_CHARGE_W * 0.4)},
            "temp_0_to_10": {"soc_0_to_90": int(MAX_CHARGE_W * 0.6), "soc_90_to_100": int(MAX_CHARGE_W * 0.2)},
            "temp_under_0": {"soc_0_to_90": int(MAX_CHARGE_W * 0.2), "soc_90_to_100": int(MAX_CHARGE_W * 0.1)}
        }
    }
    save_battery_experience(default_exp)
    return default_exp

def save_battery_experience(data):
    try:
        with open(BATTERY_EXP_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(get_msg("mem_err", e=e))

def find_charge_experience(experience, temp, soc):
    if temp >= 10:
        temp_key = "temp_over_10"
    elif 0 <= temp < 10:
        temp_key = "temp_0_to_10"
    else:
        temp_key = "temp_under_0"

    if soc < 90:
        soc_key = "soc_0_to_90"
    else:
        soc_key = "soc_90_to_100"

    return experience["max_charge_rate"][temp_key][soc_key]

def save_to_csv(data):
    write_header = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(data)

    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 50 * 1024 * 1024:
            print(get_msg("csv_trimming"))
            df = pd.read_csv(LOG_FILE)
            df.tail(20000).to_csv(LOG_FILE, index=False)
            print(get_msg("csv_trimmed"))
    except Exception as e:
        print(get_msg("csv_err", e=e))

# =====================================================================
# HELPER FUNCTIONS (API)
# =====================================================================
def set_ha_entity_value(domain, service, entity_id, param_name, value):
    """Sender et servicekald til Home Assistant REST API."""
    url = f"http://{HA_IP}:{HA_PORT}/api/services/{domain}/{service}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "content-type": "application/json"}
    payload = {"entity_id": entity_id, param_name: value}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"⚠️ Fejl ved opdatering af {entity_id}: {e}")
        return False

def load_weather_backup_state():
    """Henter information om, hvorvidt vejret har overstyret profilen."""
    if os.path.exists(WEATHER_STATE_FILE):
        try:
            with open(WEATHER_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_weather_backup_state(data):
    """Gemmer den oprindelige profil forud for uvejr."""
    try:
        with open(WEATHER_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Fejl ved gemning af vejr-tilstand: {e}")

def clear_weather_backup_state():
    """Fjerner vejr-overstyringsfilen, når vejret normaliseres."""
    if os.path.exists(WEATHER_STATE_FILE):
        try:
            os.remove(WEATHER_STATE_FILE)
        except Exception:
            pass

def evaluate_severe_weather(forecasts, weather_attrs, config_obj):
    """
    Evaluerer de næste timer ud fra de aktiverede triggers.
    En værdi der er tom, 'false' eller 'nej' deaktiverer automatisk triggeren.
    """
    if 'Emergency_Backup' not in config_obj:
        return False, "", 99

    sec = config_obj['Emergency_Backup']
    if not sec.getboolean('AUTO_WEATHER_BACKUP', False):
        return False, "", 99

    try:
        hours_ahead = int(sec.get('MONITOR_HOURS_AHEAD', 12))
    except ValueError:
        hours_ahead = 12

    def is_active(key):
        val = sec.get(key, '').strip().lower()
        return val in ['true', '1', 'yes', 'ja', 'on']

    wind_raw = sec.get('TRIGGER_WIND_GUST_MS', '').strip()
    trigger_wind = float(wind_raw) if wind_raw else None
    
    trigger_exceptional = is_active('TRIGGER_ON_EXCEPTIONAL')
    trigger_thunder = is_active('TRIGGER_ON_THUNDER')
    trigger_snow = is_active('TRIGGER_ON_HEAVY_SNOW')
    trigger_pouring = is_active('TRIGGER_ON_POURING')
    weather_debug = is_active('WEATHER_DEBUG')

    wind_unit = weather_attrs.get('wind_speed_unit', 'km/h').lower()
    now_dt = datetime.now()
    future_limit = now_dt + timedelta(hours=hours_ahead)

    if weather_debug:
        print(f"🔍 [VEJR-DEBUG] Analyserer {len(forecasts)} prognose-punkter (Enhed: {wind_unit}, Vind-trigger: {trigger_wind} m/s)...")

    for idx, f in enumerate(forecasts):
        t_str = f.get('datetime') or f.get('start')
        if not t_str:
            continue
        try:
            f_time = datetime.fromisoformat(str(t_str).replace('Z', '+00:00')).replace(tzinfo=None)
        except Exception:
            continue

        if f_time < now_dt:
            continue
        if f_time > future_limit:
            break

        cond = str(f.get('condition', '')).lower()
        
        raw_speed = float(f.get('wind_speed', 0.0))
        raw_gust = float(f.get('wind_gust_speed', raw_speed))
        if 'km' in wind_unit:
            gust_ms = raw_gust / 3.6
            speed_ms = raw_speed / 3.6
        else:
            gust_ms = raw_gust
            speed_ms = raw_speed

        if weather_debug:
            print(f"  Tid: {f_time.strftime('%H:00')} | Cond: {cond:<15} | Vind: {speed_ms:.1f} m/s | Gust: {gust_ms:.1f} m/s")

        if trigger_wind is not None and gust_ms >= trigger_wind:
            return True, f"Vindstød: {gust_ms:.1f} m/s @ {f_time.strftime('%H:00')}", idx + 1
        elif trigger_exceptional and cond == 'exceptional':
            return True, f"Farevarsel ('exceptional') @ {f_time.strftime('%H:00')}", idx + 1
        elif trigger_thunder and cond in ['lightning', 'lightning-rainy']:
            return True, f"Tordenvejr ('{cond}') @ {f_time.strftime('%H:00')}", idx + 1
        elif trigger_snow and cond in ['snowy-heavy', 'snowy-rainy']:
            return True, f"Kraftig sne ('{cond}') @ {f_time.strftime('%H:00')}", idx + 1
        elif trigger_pouring and cond == 'pouring':
            return True, f"Skybrud ('pouring') @ {f_time.strftime('%H:00')}", idx + 1

    return False, "", 0

def get_actual_temperature():
    val = get_ha_state(SENSOR_UDE_TEMP, 'float')
    if val != 0.0:
        return val
    attrs = get_ha_attributes(SENSOR_VEJR)
    return attrs.get('temperature', 10.0)

HA_STATE_CACHE = {}

def fetch_all_ha_states():
    global HA_STATE_CACHE
    url = f"http://{HA_IP}:{HA_PORT}/api/states"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "content-type": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            states_list = response.json()
            HA_STATE_CACHE = {item['entity_id']: item for item in states_list}
            return True
    except Exception as e:
        print(f"⚠️ Fejl ved hentning af samlet state cache: {e}")
    HA_STATE_CACHE = {}
    return False

def get_ha_state(entity_id, return_type='float', use_cache=True):
    if use_cache and HA_STATE_CACHE and entity_id in HA_STATE_CACHE:
        val = HA_STATE_CACHE[entity_id].get('state', '0')
    else:
        url = f"http://{HA_IP}:{HA_PORT}/api/states/{entity_id}"
        headers = {"Authorization": f"Bearer {HA_TOKEN}", "content-type": "application/json"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                val = response.json().get('state', '0')
            else:
                val = '0'
        except:
            val = '0'

    if val in ['unknown', 'unavailable', 'None', '']:
        return 0.0 if return_type == 'float' else "Smart Selvforsyning"
    try:
        return float(val) if return_type == 'float' else val
    except ValueError:
        return 0.0 if return_type == 'float' else val

def get_ha_attributes(entity_id):
    if HA_STATE_CACHE and entity_id in HA_STATE_CACHE:
        return HA_STATE_CACHE[entity_id].get('attributes', {})

    url = f"http://{HA_IP}:{HA_PORT}/api/states/{entity_id}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "content-type": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('attributes', {})
    except:
        pass
    return {}

def get_weather_forecast():
    url = f"http://{HA_IP}:{HA_PORT}/api/services/weather/get_forecasts?return_response=true"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "content-type": "application/json"}
    payload = {"type": "hourly", "entity_id": SENSOR_VEJR}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'service_response' in data and SENSOR_VEJR in data['service_response']:
                return data['service_response'][SENSOR_VEJR].get('forecast', [])
    except:
        pass
    return []

def fetch_universal_prices(sensor_now, sensors_tomorrow_str):
    """Fetches and extracts raw price arrays from various European HA integrations, filtering duplicates."""
    all_entries = []

    # 1. Fetch from the primary current price sensor
    attrs_now = get_ha_attributes(sensor_now)
    if attrs_now:
        for key in ['prices', 'prices_today', 'raw_today', 'price_info', 'normal', 'prices_tomorrow', 'raw_tomorrow']:
            if key in attrs_now and isinstance(attrs_now[key], list):
                all_entries.extend(attrs_now[key])

    # 2. Fetch from explicit tomorrow sensors if provided (e.g., Stromligning setup)
    if sensors_tomorrow_str:
        tomorrow_sensors = [s.strip() for s in sensors_tomorrow_str.split(',') if s.strip()]
        for s_name in tomorrow_sensors:
            attrs_tom = get_ha_attributes(s_name)
            if attrs_tom:
                for key in ['prices', 'prices_tomorrow', 'raw_tomorrow', 'prices_today', 'price_info', 'normal']:
                    if key in attrs_tom and isinstance(attrs_tom[key], list):
                        all_entries.extend(attrs_tom[key])

    # 3. Deduplicate, filter past hours, and sort to prevent midnight overlaps
    from datetime import datetime
    now = datetime.now()
    unique_prices = {}

    for item in all_entries:
        if not isinstance(item, dict):
            continue

        # Locate the timestamp key
        time_str = item.get('start') or item.get('time') or item.get('hour')
        if not time_str:
            continue

        try:
            # Parse time, handle standard ISO formats, and STRIP timezone (make naive)
            start_time = datetime.fromisoformat(str(time_str).replace('Z', '+00:00')).replace(tzinfo=None)

            # Keep the price if it is from today onwards (so we can learn full 24-hour tariffs)
            if start_time >= now.replace(hour=0, minute=0, second=0, microsecond=0):
                # Use a normalized string as key so valid tomorrow-data overwrites dummy 0.00 data
                norm_key = start_time.strftime("%Y-%m-%d %H:%M")
                unique_prices[norm_key] = item
        except (KeyError, ValueError, TypeError):
            continue

    # Return as a chronologically sorted list
    sorted_prices = [unique_prices[k] for k in sorted(unique_prices.keys())]
    return sorted_prices

def build_time_price_dict(price_array):
    """Normalizes variation in JSON keys across different integrations into a standardized hourly price dictionary"""
    p_dict = {}
    for p in price_array:
        if not isinstance(p, dict): continue
        try:
            # Detect time stamp key variations
            start_str = p.get('start') or p.get('datetime') or p.get('time') or p.get('startsAt') or p.get('period_start') or p.get('hour')
            if not start_str: continue

            dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            key = dt.strftime("%Y-%m-%d %H")

            # Detect price key variations
            price_val = p.get('price') or p.get('value') or p.get('total') or p.get('amount')
            if price_val is None: continue

            if key not in p_dict: p_dict[key] = []
            p_dict[key].append(float(price_val))
        except:
            pass
    return {k: sum(v)/len(v) for k, v in p_dict.items() if v}

def build_solar_dict(ml_forecast_data):
    s_dict_watts = {}
    for time_str, watt in ml_forecast_data.items():
        try:
            dt = datetime.fromisoformat(time_str)
            key = dt.strftime("%Y-%m-%d %H")
            if key not in s_dict_watts:
                s_dict_watts[key] = []
            s_dict_watts[key].append(watt)
        except:
            pass

    s_dict_kwh = {}
    for key, watts_list in s_dict_watts.items():
        if not watts_list: continue
        avg_watts = sum(watts_list) / len(watts_list)
        s_dict_kwh[key] = avg_watts / 1000.0
    return s_dict_kwh

def build_weather_dict(forecasts):
    v_dict = {}
    for f in forecasts:
        try:
            dt = datetime.fromisoformat(f.get('datetime').replace('Z', '+00:00')).replace(tzinfo=None)
            key = dt.strftime("%Y-%m-%d %H")
            v_dict[key] = f.get('temperature', 10.0)
        except:
            pass
    return v_dict

def get_max_peak_in_window(current_now, hours_ahead, price_dict):
    """Finds the maximum peak price within a time window using the normalized price dictionary"""
    start_hour = current_now.replace(minute=0, second=0, microsecond=0)
    future_limit = start_hour + timedelta(hours=hours_ahead)
    relevant_prices = []

    for time_str, price in price_dict.items():
        try:
            start_dt = datetime.strptime(time_str, "%Y-%m-%d %H")
            if start_hour <= start_dt < future_limit:
                relevant_prices.append(float(price))
        except:
            pass

    return max(relevant_prices) if relevant_prices else 0.0
# =====================================================================
# MAIN ENGINE
# =====================================================================
print(get_msg("start"))
print(get_msg("log_path", path=os.path.abspath(LOG_FILE)))

print(f"☀️ Active Primary Forecast Sensor: {SENSOR_SOL_PRIMARY or 'None (Using Fallbacks Only)'}")
print(f"🌤️ Active Fallback Forecast Sensors: {RAW_FORECASTS or 'None'}")

# Initialize ML Model variables outside the loop
ml_model = None
last_model_mtime = 0.0
temp_col_name = None
model_sidst_traenet = "Ukendt"

while True:
    try:
        now = datetime.now()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        rolling_data = load_rolling_log()
        if not rolling_data.get("history"):
            rolling_data = backfill_rolling_log_from_csv(rolling_data, now)
        print(f"\n===================================================================")
        print(get_msg("wake", time=now.strftime('%Y-%m-%d %H:%M:%S')))
        print(f"===================================================================")

        # --- UPDATE HA STATE CACHE ---
        print("📥 Henter alle Home Assistant tilstande på én gang (Cache)...")
        fetch_all_ha_states()

        # --- LOAD ML MODEL IF CHANGED ---
        try:
            model_file = os.path.join(script_dir, 'ml_solcelle_model.pkl')
            model_mtime = os.path.getmtime(model_file)
            
            if ml_model is None or model_mtime > last_model_mtime:
                print(f"🔄 Indlæser ML-model (Ændret: {datetime.fromtimestamp(model_mtime).strftime('%Y-%m-%d %H:%M:%S')})...")
                with open(model_file, 'rb') as f:
                    ml_model = pickle.load(f)
                ml_features = ml_model.feature_names_in_
                temp_col_name = [f for f in ml_features if f not in ['hour', 'month', 'weekday', 'is_weekend']][0]
                last_model_mtime = model_mtime
                model_sidst_traenet = datetime.fromtimestamp(model_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except FileNotFoundError:
            if ml_model is None:
                print(get_msg("err_model"))
                time.sleep(60)
                continue
            else:
                print("⚠️ Advarsel: 'ml_solcelle_model.pkl' ikke fundet på disk. Bruger forrige version fra hukommelsen.")
        except Exception as e:
            if ml_model is None:
                print(get_msg("err_model_load", e=e))
                time.sleep(60)
                continue
            else:
                print(f"⚠️ Advarsel: Fejl ved indlæsning af model. Bruger forrige version fra hukommelsen. Fejl: {e}")

        # --- FETCH SENSORS FROM HA ---
        current_temp = get_actual_temperature()
        battery_soc = get_ha_state(SENSOR_SOC)

        # --- FETCH HARDWARE SPECS FROM CONFIG.INI ---
        try:
            NOMINAL_CAPACITY = float(config['Hardware'].get('BATTERY_CAPACITY_KWH', 20.0))
            batt_price = float(config['Hardware'].get('BATTERY_PRICE_KR', 64000.0))
            batt_cycles = float(config['Hardware'].get('BATTERY_CYCLES', 6000.0))
        except ValueError:
            print("⚠️ Advarsel: Kunne ikke læse hardware-tal fra config.ini (Tjek for bogstaver i tallene). Bruger standard.")
            NOMINAL_CAPACITY, batt_price, batt_cycles = 20.0, 64000.0, 6000.0

        battery_experience_now = get_battery_experience(NOMINAL_CAPACITY)

        if current_temp >= 10:
            cap_mult = battery_experience_now["temp_capacity_multipliers"]["temp_over_10"]
        elif 0 <= current_temp < 10:
            cap_mult = battery_experience_now["temp_capacity_multipliers"]["temp_0_to_10"]
        else:
            cap_mult = battery_experience_now["temp_capacity_multipliers"]["temp_under_0"]

        BATTERY_CAPACITY_KWH = battery_experience_now["learned_capacity"] * cap_mult

        if NOMINAL_CAPACITY > 0 and batt_cycles > 0 and batt_price > 0:
            degradation_price = batt_price / (NOMINAL_CAPACITY * batt_cycles)
        else:
            degradation_price = 0.0

        software_min_soc = get_ha_state(SENSOR_MIN_SOC, 'float')
        hardware_min_soc = get_ha_state(SENSOR_INVERTER_MIN_SOC, 'float')

        # 1:1 Synkronisering: Hvis HA-skyderen ændres, opdateres inverterens hardware-register
        if software_min_soc > 0.0 and SENSOR_INVERTER_MIN_SOC:
            if abs(software_min_soc - hardware_min_soc) >= 1.0:
                print(f"🔄 Synkroniserer Inverter SOC: Hardware ({hardware_min_soc}%) -> Software ({software_min_soc}%)")
                if set_ha_entity_value("number", "set_value", SENSOR_INVERTER_MIN_SOC, "value", int(software_min_soc)):
                    hardware_min_soc = software_min_soc

        min_soc_val = max(software_min_soc, hardware_min_soc)
        if min_soc_val <= 0.0:
            min_soc_val = 15.0

        min_soc_val = max(software_min_soc, hardware_min_soc)
        if min_soc_val <= 0.0:
            min_soc_val = 15.0
        # --- LÆS DYNAMISK BUFFER ---
        salgs_buffer = get_ha_state(SENSOR_SALGS_BUFFER, 'float')
        if salgs_buffer <= 0.0:
            salgs_buffer = 5.0 # Sikkerheds-fallback

        user_sol_factor_pct = get_ha_state(SENSOR_SOL_FAKTOR_BOX, 'float')
        if user_sol_factor_pct <= 0.0:
            user_sol_factor_pct = 150.0
        bruger_sol_faktor = user_sol_factor_pct / 100.0

        min_export_price = get_ha_state(SENSOR_MIN_EKSPORT, 'float')
        throttle_aggression = get_ha_state(SENSOR_THROTTLE_AGGRESSION, 'float')
        throttle_min_soc = get_ha_state("input_number.sol_throttle_min_soc", 'float')
        if throttle_min_soc <= 0.0:
            throttle_min_soc = 20.0
        throttle_hysteresis_target = throttle_min_soc + 3.0
        if throttle_aggression < 0.0:
            throttle_aggression = 0.0

        sol_laas_threshold = get_ha_state(SENSOR_SOL_LAAS_MIN_SOC, 'float')
        if sol_laas_threshold <= 0.0:
            sol_laas_threshold = 40.0

        red_profit_margin = get_ha_state(SENSOR_ROED_PROFIT, 'float')
        if red_profit_margin <= 0.0:
            red_profit_margin = 1.0

        green_min_sell_price = get_ha_state(SENSOR_GROEN_MIN_SALG, 'float')
        if green_min_sell_price <= 0.0:
            green_min_sell_price = 1.5

        tvangsladning_pris = get_ha_state(SENSOR_TVANGSLADNING, 'float')
        if tvangsladning_pris > 0.0:
            tvangsladning_pris = -0.50 # Sikkerheds-fallback

        throttle_pris_dyk = get_ha_state(SENSOR_THROTTLE_PRIS_DYK, 'float')
        if throttle_pris_dyk <= 0.0:
            throttle_pris_dyk = 0.30 # Safety fallback

        price_now_ex = get_ha_state(SENSOR_PRIS_NU_EX)
        price_now_inc = get_ha_state(SENSOR_PRIS_NU_INKL)
        valgt_profil = get_ha_state(SENSOR_PROFIL, 'text')

        current_plan_state = get_ha_state("sensor.solplanet_automation_plan", 'text')
        current_plan_attrs = get_ha_attributes("sensor.solplanet_automation_plan")
        current_action_id = current_plan_attrs.get("action_id", 1)

        is_currently_selling = current_action_id in [4, 11] # 4=Salg, 11=Pre-dump
        is_currently_export_stopped = "Eksport Stop" in current_plan_state

        pv_w = get_ha_state(SENSOR_PV)
        p1_w = get_ha_state(SENSOR_P1)
        batt_w = get_ha_state(SENSOR_BATT_PWR)

        # Initialize EV power to an absolute float zero before math to prevent crashes
        ev_total_w = 0.0

        # Only attempt API calls if the user actually has EV chargers configured in W
        if EV_SENSORS_W:
            for s in EV_SENSORS_W:
                state = get_ha_state(s)
                if state is not None:
                    try:
                        ev_total_w += float(state)
                    except ValueError:
                        pass

        # Only attempt API calls if the user actually has EV chargers configured in kW
        if EV_SENSORS_KW:
            for s in EV_SENSORS_KW:
                state = get_ha_state(s)
                if state is not None:
                    try:
                        ev_total_w += (float(state) * 1000.0)
                    except ValueError:
                        pass

        total_house_w = pv_w + p1_w + batt_w
        naked_house_w = max(0.0, total_house_w - ev_total_w)

        # Fetch charger statuses for solar bypass (5 = Solar charging)
        is_ev_solar_charging = False
        if EV_STATUS_SENSORS:
            for s in EV_STATUS_SENSORS:
                try:
                    if int(get_ha_attributes(s).get("status_id", 1)) == 5:
                        is_ev_solar_charging = True
                        break
                except (TypeError, ValueError):
                    pass

        ev_shield_mode = get_ha_state(SENSOR_EV_MODE, 'text')
        ev_shield_threshold = get_ha_state(SENSOR_EV_THRESHOLD, 'float')
        if ev_shield_threshold < 1000:
            ev_shield_threshold = 10000.0

        # --- PRICES AND WEATHER ---
        # Fetch and parse buy prices (Universal)
        buy_raw_data = fetch_universal_prices(SENSOR_PRIS_NU_INKL, SENSOR_PRIS_TOMORROW_INKL)
        buy_dict = build_time_price_dict(buy_raw_data)

        # Fetch and parse sell prices (Universal)
        sell_raw_data = fetch_universal_prices(SENSOR_PRIS_NU_EX, SENSOR_PRIS_TOMORROW_EX)
        sell_dict = build_time_price_dict(sell_raw_data)

        # --- NY DYNAMISK FALLBACK MED NESTED TARIFF-SUPPORT ---
        buy_attrs = get_ha_attributes(SENSOR_PRIS_NU_INKL)
        eds_main_tariffs = buy_attrs.get('tariffs', {})

        # EDS lægger tarifferne ind i et ekstra 'tariffs' lag. Vi tjekker om dette nested lag findes:
        if 'tariffs' in eds_main_tariffs:
            eds_hourly_tariffs = eds_main_tariffs.get('tariffs', {})
            eds_add_tariffs = eds_main_tariffs.get('additional_tariffs', {})
        else:
            eds_hourly_tariffs = eds_main_tariffs
            eds_add_tariffs = buy_attrs.get('additional_tariffs', {})

        add_tariff_sum = sum([float(v) for v in eds_add_tariffs.values()]) if isinstance(eds_add_tariffs, dict) else 0.0

        # Calculate implied tariffs from overlapping data (Buy - Sell)
        implied_tariffs_by_hour = {}
        for tk, b_price in buy_dict.items():
            if tk in sell_dict:
                hr = str(datetime.strptime(tk, "%Y-%m-%d %H").hour)
                t_val = (float(b_price) / VAT_RATE) - float(sell_dict[tk])
                implied_tariffs_by_hour[hr] = max(0.0, t_val)

        for time_key, buy_price in buy_dict.items():
            if time_key not in sell_dict:
                hour_str = str(datetime.strptime(time_key, "%Y-%m-%d %H").hour)
                
                # Check if we got valid tariff data from EDS attributes
                if len(eds_hourly_tariffs) > 0 or add_tariff_sum > 0:
                    hour_tariff = float(eds_hourly_tariffs.get(hour_str, 0.0)) if isinstance(eds_hourly_tariffs, dict) else 0.0
                    total_tariff = hour_tariff + add_tariff_sum
                else:
                    # Use dynamically calculated tariff from today's matching hour
                    total_tariff = implied_tariffs_by_hour.get(hour_str, 0.0)

                # I DK tillægges tariffer og spotpris FØR momsen beregnes.
                # For at finde den rene spotpris: (Købspris / moms) - Tariffer
                ren_spotpris = (float(buy_price) / VAT_RATE) - total_tariff
                sell_dict[time_key] = ren_spotpris

        # Opdater den live salgspris (hjernen), hvis vi ikke har en dedikeret salgs-sensor
        if not SENSOR_PRIS_NU_EX:
            price_now_ex = sell_dict.get(now.strftime("%Y-%m-%d %H"), 0.0)

        # Opdater den live salgspris (hjernen), hvis vi ikke har en dedikeret salgs-sensor
        if not SENSOR_PRIS_NU_EX:
            price_now_ex = sell_dict.get(now.strftime("%Y-%m-%d %H"), 0.0)

        forecasts_list = get_weather_forecast()
        weather_dict = build_weather_dict(forecasts_list)

        # --- AUTOMATISK UVEJRS-OVERVÅGNING & BACKUP OVERSTYRING ---
        weather_attrs = get_ha_attributes(SENSOR_VEJR)
        storm_active, storm_reason, _ = evaluate_severe_weather(forecasts_list, weather_attrs, config)
        saved_weather_state = load_weather_backup_state()

        if storm_active:
            storm_target = float(config['Emergency_Backup'].get('WEATHER_TARGET_SOC', 90.0))
            if valgt_profil != "Backup Mode":
                print(f"🚨 UVEJR VARSLET: {storm_reason}! Skifter til Backup Mode...")
                save_weather_backup_state({
                    "original_profile": valgt_profil,
                    "activated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "reason": storm_reason
                })
                set_ha_entity_value("input_select", "select_option", SENSOR_PROFIL, "option", "Backup Mode")
                valgt_profil = "Backup Mode"

            # Tving minimums-SOC op på uvejrsmålet under alarmen
            min_soc_val = max(min_soc_val, storm_target)

        elif saved_weather_state is not None:
            # Uvejret er drevet over (og er ikke varslet i overvågningsvinduet)
            orig_prof = saved_weather_state.get("original_profile", "Smart Selvforsyning")
            print(f"🌤️ Uvejr drevet over. Ruller automatisk tilbage til: {orig_prof}")
            set_ha_entity_value("input_select", "select_option", SENSOR_PROFIL, "option", orig_prof)
            valgt_profil = orig_prof
            clear_weather_backup_state()

        # =====================================================================
        # API SANITY CHECK (BLACKOUT GUARD)
        # =====================================================================
        # Check if dictionaries are completely empty. A real price of 0.0 is valid,
        # but 0 length means the API integration failed or timed out.
        if len(buy_dict) == 0 or len(sell_dict) == 0:
            handling = "⚠️ API Error: Missing price data. Forcing safe Self-consumption."
            print("\n❌ CRITICAL: API Blackout detected! Price dictionaries are empty. Activating emergency protocol.")

            # Send emergency status to Home Assistant
            headers = {"Authorization": f"Bearer {HA_TOKEN}", "content-type": "application/json"}
            payload = {
                "state": handling,
                "attributes": {
                    "friendly_name": "Intelligent Solcellestyring (ML)",
                    "icon": "mdi:alert-network",
                    "sidst_opdateret": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "target_work_mode": "Self-consumption",
                    "target_battery_input_power": 10000,
                    "target_battery_output_power": MAX_DISCHARGE_W,
                    "action_id": 1
                }
            }
            try:
                requests.post(HA_URL, headers=headers, json=payload, timeout=10)
            except:
                pass

            # Log the emergency state to CSV
            log_entry = {
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "profil": valgt_profil,
                "batteri_soc": battery_soc,
                "pris_koeb_inkl_moms": 0.0,
                "pris_salg_ex_moms": 0.0,
                "sol_prognose_nu_w": 0.0,
                "sol_rest_idag_kwh": 0.0,
                "sol_faktor_prognose": 1.0,
                "hus_forbrug_nu_w": naked_house_w,
                "pv_produktion_nu_w": pv_w,
                "p1_grid_nu_w": p1_w,
                "batteri_watt_nu": batt_w,
                "ev_forbrug_total_w": ev_total_w,
                "throttle_safety_price": 0.0,
                "min_eksport_pris_limit": min_export_price,
                "action_id": 1,
                "target_mode": "Self-consumption",
                "target_charge_w": 10000,
                "beslutning_tekst": handling,
                "udendoers_temp": current_temp
            }
            save_to_csv(log_entry)

            print(get_msg("sleep"))
            # Sleep for approx 3 minutes, but watch the dashboard trigger button
            for _ in range(36):
                time.sleep(5)
                if get_ha_state("input_boolean.trigger_ai_beregning", "text", use_cache=False) == "on":
                    print("\n⚡ MANUAL RETRY TRIGGERED FROM DASHBOARD! Attempting to fetch prices again...")
                    try:
                        requests.post(f"http://{HA_IP}:{HA_PORT}/api/services/input_boolean/turn_off", headers=headers, json={"entity_id": "input_boolean.trigger_ai_beregning"}, timeout=10)
                    except:
                        pass
                    break

            continue # Restart the while True loop from the top!

        # =====================================================================
        # HYBRID SOLAR FORECAST ENGINE (Universal Parser)
        # =====================================================================
        solar_dict = {}

        def parse_forecast_data(attrs):
            """Universal detector for Solcast, Forecast.Solar, Open-Meteo, and Custom ML models"""
            extracted = {}
            if 'detailedForecast' in attrs: # Solcast format (Hourly Power)
                for entry in attrs['detailedForecast']:
                    try:
                        dt = datetime.fromisoformat(entry.get('period_start').replace('Z', '+00:00'))
                        key = dt.strftime("%Y-%m-%d %H")
                        extracted[key] = extracted.get(key, 0.0) + float(entry.get('pv_estimate', 0.0))
                    except: pass
            elif 'wh_period' in attrs: # Forecast.Solar format (Energy steps)
                for t_str, wh in attrs['wh_period'].items():
                    try:
                        dt = datetime.fromisoformat(t_str.replace('Z', '+00:00'))
                        key = dt.strftime("%Y-%m-%d %H")
                        extracted[key] = extracted.get(key, 0.0) + (float(wh) / 1000.0)
                    except: pass
            elif 'watts' in attrs: # HA Standard / Custom ML format (Power snapshots)
                # Group sub-hour entries (e.g., 15-min intervals) to average the power instead of summing it
                temp_watts = {}
                for t_str, w in attrs['watts'].items():
                    try:
                        dt = datetime.fromisoformat(t_str.replace('Z', '+00:00'))
                        key = dt.strftime("%Y-%m-%d %H")
                        if key not in temp_watts:
                            temp_watts[key] = []
                        temp_watts[key].append(float(w))
                    except: pass

                # Calculate the true average power for the hour in kW
                for key, w_list in temp_watts.items():
                    if w_list:
                        extracted[key] = (sum(w_list) / len(w_list)) / 1000.0
            return extracted

        # 1. Fetch fallback forecasts (Combines them automatically if users have East/West strings)
        for s_fallback in RAW_FORECASTS:
            fb_data = parse_forecast_data(get_ha_attributes(s_fallback))
            for key, kwh in fb_data.items():
                solar_dict[key] = solar_dict.get(key, 0.0) + kwh

        # 2. Hent primær prognose (Din egen model eller hoved-inverteren)
        if SENSOR_SOL_PRIMARY and SENSOR_SOL_PRIMARY.strip() != "":
            prim_data = parse_forecast_data(get_ha_attributes(SENSOR_SOL_PRIMARY))
            # Primær data overskriver altid fallbacks for de timer, hvor den har et bud
            for key, kwh in prim_data.items():
                solar_dict[key] = kwh

        solar_expected = sum([v for k, v in solar_dict.items() if k.startswith(now.strftime("%Y-%m-%d")) and int(k.split()[1]) >= now.hour])

        # --- PRE-CALCULATE ML LOAD FORECAST FOR NEXT 48 HOURS (BATCH) ---
        ml_predictions_w = {}
        if ml_model is not None:
            future_hours_data = []
            future_keys = []
            for i in range(1, 49):
                future = now + timedelta(hours=i)
                key = future.strftime("%Y-%m-%d %H")
                t_temp = weather_dict.get(key, 10.0)
                future_hours_data.append({
                    'hour': future.hour,
                    'month': future.month,
                    'weekday': future.weekday(),
                    'is_weekend': 1 if future.weekday() >= 5 else 0,
                    temp_col_name: t_temp
                })
                future_keys.append(key)
            
            df_future = pd.DataFrame(future_hours_data)
            preds = ml_model.predict(df_future)
            for k, p in zip(future_keys, preds):
                ml_predictions_w[k] = p

        # --- CONSUMPTION FORECAST ---
        load_night_w = 0.0
        load_day_w = 0.0
        load_rest_today_w = 0.0
        solar_tomorrow_w = 0.0

        morning_time = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if now.hour >= 6:
            morning_time += timedelta(days=1)
        evening_time = morning_time.replace(hour=20)

        hours_ahead = int((evening_time - now).total_seconds() / 3600) + 1

        for i in range(1, hours_ahead + 1):
            future = now + timedelta(hours=i)
            key = future.strftime("%Y-%m-%d %H")
            t_solar = solar_dict.get(key, 0.0) * 1000.0
            t_temp = weather_dict.get(key, 10.0)

            t_load = ml_predictions_w.get(key, 0.0)

            if future <= morning_time:
                load_night_w += t_load
            elif morning_time < future <= evening_time:
                load_day_w += t_load
                solar_tomorrow_w += t_solar

            if future.date() == now.date():
                load_rest_today_w += t_load

        load_night_kwh = load_night_w / 1000.0
        load_day_kwh = load_day_w / 1000.0
        solar_tomorrow_kwh = solar_tomorrow_w / 1000.0
        load_rest_today_kwh = load_rest_today_w / 1000.0

        # --- MORGENSPIDS (06-08) FORBRUG OG RESERVE ---
        # Beregn ML-forbrug i morgenspidsen (kl. 06:00 - 08:00)
        load_morning_peak_w = 0.0
        for h in [6, 7]:
            t_key = (morning_time.replace(hour=h)).strftime("%Y-%m-%d %H")
            load_morning_peak_w += ml_predictions_w.get(t_key, 0.0)
        load_morning_peak_kwh = load_morning_peak_w / 1000.0

        # Minimum batteri ved kl. 06 skal dække morgenspidsen (06-08) + min_soc
        min_reserve_morning_kwh = load_morning_peak_kwh + ((min_soc_val / 100.0) * BATTERY_CAPACITY_KWH)
        morning_reserve_soc = max(min_soc_val, (min_reserve_morning_kwh / BATTERY_CAPACITY_KWH) * 100.0)

        morning_req_kwh = load_night_kwh + ((morning_reserve_soc / 100.0) * BATTERY_CAPACITY_KWH)
        green_target_soc = min(100.0, (morning_req_kwh / BATTERY_CAPACITY_KWH) * 100.0)

        now_battery_kwh = BATTERY_CAPACITY_KWH * (battery_soc / 100.0)
        expected_morning_kwh = max((min_soc_val/100.0)*BATTERY_CAPACITY_KWH, now_battery_kwh - load_night_kwh)
        surplus_solar_kwh = max(0.0, solar_tomorrow_kwh - load_day_kwh)
        room_in_battery_kwh = BATTERY_CAPACITY_KWH - expected_morning_kwh
        missing_from_grid_kwh = room_in_battery_kwh - surplus_solar_kwh

        if missing_from_grid_kwh <= 0:
            night_target_soc = morning_reserve_soc
        else:
            night_target_kwh = expected_morning_kwh + missing_from_grid_kwh
            night_target_soc = (night_target_kwh / BATTERY_CAPACITY_KWH) * 100.0
            night_target_soc = min(100.0, max(morning_reserve_soc, night_target_soc))

        if solar_tomorrow_kwh > (load_day_kwh * 2.0) and valgt_profil == "Smart Selvforsyning":
             night_target_soc = morning_reserve_soc

        if valgt_profil == "Backup Mode":
            night_target_soc = max(50.0, night_target_soc)

        # Hent alle fremtidige priser til min_future_buy_price
        future_prices = []
        for k, v in buy_dict.items():
            p_time = datetime.strptime(k, "%Y-%m-%d %H")
            if current_hour <= p_time <= now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1):
                future_prices.append({'time': p_time, 'price': v})

        if future_prices:
            min_future_buy_price = min([p['price'] for p in future_prices])
        else:
            min_future_buy_price = price_now_inc

        # =====================================================================
        # DYNAMIC MARGINAL COST (SOLAR VS GRID)
        # =====================================================================
        room_in_battery_now_kwh = BATTERY_CAPACITY_KWH * ((100.0 - battery_soc) / 100.0)
        total_need_tomorrow_kwh = load_day_kwh + room_in_battery_now_kwh
        house_lacks_power_tomorrow = (total_need_tomorrow_kwh * 1.1) > solar_tomorrow_kwh

        if house_lacks_power_tomorrow:
            energy_replacement_price = min_future_buy_price
        else:
            energy_replacement_price = 0.0

        total_sell_barrier = energy_replacement_price + degradation_price

        # =====================================================================
        # NEGATIVE PRICE GUARD & PRE-DUMP STRATEGY (KNIVSÆGGEN)
        # =====================================================================
        negative_hours = []
        for k, v in buy_dict.items():
            hour_time = datetime.strptime(k, "%Y-%m-%d %H")
            if v <= tvangsladning_pris and hour_time > current_hour:
                negative_hours.append(hour_time)

        is_tvangsladning_now = price_now_inc <= tvangsladning_pris
        is_pre_dump_now = False

        if not is_tvangsladning_now and negative_hours:
            first_neg_time = min(negative_hours)
            if (first_neg_time - now).total_seconds() < 12 * 3600:
                sell_prices_before_neg = []
                for k, v in sell_dict.items():
                    p_time = datetime.strptime(k, "%Y-%m-%d %H")
                    if current_hour <= p_time < first_neg_time:
                        sell_prices_before_neg.append({'time': p_time, 'price': v})

                if sell_prices_before_neg:
                    best_sell_hour = max(sell_prices_before_neg, key=lambda x: x['price'])
                    if best_sell_hour['time'].hour == now.hour and best_sell_hour['time'].day == now.day:
                        if battery_soc > (min_soc_val + 5.0) and price_now_ex >= min_export_price:
                            is_pre_dump_now = True

        # =====================================================================
        # DYNAMIC NIGHT-TIME CHEAP HOUR SELECTION (STRIKT KUN NAT: KL. 23-06)
        # =====================================================================
        selected_charge_hours = []
        selected_afternoon_hours = []
        missing_kwh_for_night = max(0.0, BATTERY_CAPACITY_KWH * ((night_target_soc - battery_soc) / 100.0))

        # Filtrer fremtidige priser, så KUN reelle nattimer (kl. 23-06) kan vælges til natladning
        night_prices = [p for p in future_prices if (p['time'].hour < 6 or p['time'].hour >= 23)]

        if night_prices and missing_kwh_for_night > 0.5:
            night_prices_sorted = sorted(night_prices, key=lambda x: x['price'])
            cheapest_night_price = night_prices_sorted[0]['price']
            morning_prices = [p['price'] for p in future_prices if p['time'].hour in [6, 7, 8]]

            most_expensive_morning_price = max(morning_prices) if morning_prices else cheapest_night_price

            is_winter = now.month in [10, 11, 12, 1, 2, 3]
            price_threshold = 0.15 if is_winter else degradation_price

            if (most_expensive_morning_price - cheapest_night_price) >= price_threshold or valgt_profil == "Backup Mode":
                hours_needed = math.ceil(missing_kwh_for_night / (MAX_CHARGE_W / 1000.0))
                hours_needed = max(1, hours_needed)
                selected_charge_hours = [bt['time'] for bt in night_prices_sorted[:hours_needed]]

        if 6 <= now.hour <= 18:
            sol_faktor = (solar_expected / load_rest_today_kwh) if load_rest_today_kwh > 0 else 1.0
        else:
            sol_faktor = (solar_tomorrow_kwh / load_day_kwh) if load_day_kwh > 0 else 1.0

        throttle_safety_price = get_ha_state("input_number.sol_throttle_safety_price", 'float')

        handling = get_msg("normal_default")
        target_mode = "Self-consumption"
        target_charge = 10000
        target_discharge = MAX_DISCHARGE_W
        action_id = 1
        is_now_cheapest = False
        smart_night_charge_w = MAX_CHARGE_W

        if missing_kwh_for_night > 0.5 and selected_charge_hours:
            for selected_time in selected_charge_hours:
                if selected_time.hour == now.hour and selected_time.day == now.day:
                    is_now_cheapest = True
                    future_charge_hours = [t for t in selected_charge_hours if t >= current_hour]
                    hours_left = max(1, len(future_charge_hours))
                    ideal_charge_w = ((missing_kwh_for_night / hours_left) * 1000.0) + 200
                    smart_night_charge_w = int(max(1000, min(MAX_CHARGE_W, ideal_charge_w)))
                    break

        smart_afternoon_charge_w = 0
        is_now_cheapest_afternoon = False
        if 6 <= now.hour < 17:
            solar_to_17_kwh = sum([v for k, v in solar_dict.items() if k.startswith(now.strftime("%Y-%m-%d")) and now.hour <= int(k.split()[1]) < 17])
            load_to_17_w = 0.0
            for i in range(17 - now.hour):
                future = now + timedelta(hours=i)
                key_temp = future.strftime("%Y-%m-%d %H")
                load_to_17_w += ml_predictions_w.get(key_temp, 0.0)
            load_to_17_kwh = load_to_17_w / 1000.0

            expected_kwh_at_17 = min(BATTERY_CAPACITY_KWH, max(0.0, (battery_soc / 100.0) * BATTERY_CAPACITY_KWH + solar_to_17_kwh - load_to_17_kwh))
            solar_evening_kwh = sum([v for k, v in solar_dict.items() if k.startswith(now.strftime("%Y-%m-%d")) and 17 <= int(k.split()[1]) < 21])

            load_evening_w = 0.0
            for i in range(17, 21):
                if i <= now.hour: continue
                future = now.replace(hour=i, minute=0, second=0, microsecond=0)
                key_temp = future.strftime("%Y-%m-%d %H")
                load_evening_w += ml_predictions_w.get(key_temp, 0.0)
            load_evening_kwh = load_evening_w / 1000.0

            min_reserve_kwh = (min_soc_val / 100.0) * BATTERY_CAPACITY_KWH
            needed_for_evening_kwh = max(0.0, load_evening_kwh - solar_evening_kwh)
            available_at_17_kwh = max(0.0, expected_kwh_at_17 - min_reserve_kwh)
            missing_for_evening_kwh = max(0.0, needed_for_evening_kwh - available_at_17_kwh)

            if missing_for_evening_kwh > 0.5:
                future_prices_afternoon = [{'time': datetime.strptime(k, "%Y-%m-%d %H"), 'price': v} for k, v in buy_dict.items() if current_hour <= datetime.strptime(k, "%Y-%m-%d %H") < now.replace(hour=17, minute=0, second=0, microsecond=0)]
                evening_prices = [v for k, v in buy_dict.items() if now.strftime("%Y-%m-%d") in k and 17 <= int(k.split()[-1]) < 21]
                max_evening_price = max(evening_prices) if evening_prices else price_now_inc

                if future_prices_afternoon:
                    min_afternoon_price = min(future_prices_afternoon, key=lambda x: x['price'])['price']
                    is_winter = now.month in [10, 11, 12, 1, 2, 3]
                    price_diff_needed = 0.15 if is_winter else degradation_price

                    if (max_evening_price - min_afternoon_price) >= price_diff_needed:
                        future_prices_afternoon = sorted(future_prices_afternoon, key=lambda x: x['price'])
                        # Brug en roligere ladehastighed (5 kW) til time-estimat, så vi ikke udskyder alt til 1 time ved 10 kW
                        hours_needed_afternoon = max(1, math.ceil(missing_for_evening_kwh / 5.0))
                        hours_needed_afternoon = min(hours_needed_afternoon, max(1, 17 - now.hour))
                        selected_afternoon_hours = [bt['time'] for bt in future_prices_afternoon[:hours_needed_afternoon]]

                        future_aft_hours = [t for t in selected_afternoon_hours if t >= current_hour]
                        hours_left_aft = max(1, len(future_aft_hours))
                        ideal_charge_w_aft = ((missing_for_evening_kwh / hours_left_aft) * 1000.0) + 200
                        smart_afternoon_charge_w = int(max(1500, min(MAX_CHARGE_W, ideal_charge_w_aft)))

                        if current_hour in selected_afternoon_hours:
                            is_now_cheapest_afternoon = True

        smart_solar_charge_w = MAX_CHARGE_W
        is_peak_shaving = False
        if 6 <= now.hour <= 16 and sol_faktor >= bruger_sol_faktor and battery_soc < 99.0:
            cheap_solar_kwh = sum([v for k, v in solar_dict.items() if k.startswith(now.strftime("%Y-%m-%d")) and int(k.split()[-1]) >= now.hour and sell_dict.get(k, 99.0) < throttle_safety_price])
            expected_cheap_fill = cheap_solar_kwh * (throttle_aggression / 10.0)
            missing_to_full_kwh = BATTERY_CAPACITY_KWH * ((100.0 - battery_soc) / 100.0)
            rest_need_now_kwh = max(0.5, missing_to_full_kwh - expected_cheap_fill)
            hours_with_solar_left = max(1, 17 - now.hour)
            smart_solar_charge_w = int(max(200, min(MAX_CHARGE_W, (rest_need_now_kwh / hours_with_solar_left) * 1000.0)))

        print(get_msg("debug_status"))
        print(get_msg("debug_temp_soc_prof", temp=current_temp, soc=battery_soc, profil=valgt_profil))
        print(get_msg("debug_prices", k=price_now_inc, s=price_now_ex))
        print(get_msg("debug_batt_info", cap=BATTERY_CAPACITY_KWH, deg=degradation_price))
        print(get_msg("debug_raw_measurements", sol=pv_w, p1=p1_w, batt=batt_w))
        print(get_msg("debug_naked_house", house=naked_house_w))

        minutes_left_of_hour = 60 - now.minute
        max_soc_drop_now = (((MAX_DISCHARGE_W / 1000.0) * (minutes_left_of_hour / 60.0)) / BATTERY_CAPACITY_KWH) * 100.0

        solar_forecast_now = solar_dict.get(now.strftime("%Y-%m-%d %H"), 0.0) * 1000.0
        is_daytime = solar_forecast_now > 100.0 or (6 <= now.hour <= 18)
        # --- EV SHIELD LOGIC ---
        ev_shield_triggered = False
        ev_dynamic_discharge = MAX_DISCHARGE_W

        # Vi aktiverer KUN skjoldet, hvis bilerne IKKE er i gang med en sol-opladning (ID 5)
        if not is_ev_solar_charging:
            if ev_shield_mode == "Simpel (Total Forbrugsgrænse)" and total_house_w > ev_shield_threshold:
                ev_shield_triggered = True
                ev_dynamic_discharge = 0
                ev_msg = get_msg("ev_shield_simple", threshold=int(ev_shield_threshold))
            elif ev_shield_mode == "Avanceret (Målt på lader)" and ev_total_w > 500:
                ev_shield_triggered = True
                ev_dynamic_discharge = int(min(MAX_DISCHARGE_W, naked_house_w + 200))
                ev_msg = get_msg("ev_shield_advanced", w=ev_dynamic_discharge)

        # --- PRE-CALCULATION OF PEAKS & VOLUME FOR DEBUG ---
        # Aften-salg: Beregnes fra nuværende niveau til aften-mål
        available_sell_kwh_evening = max(0.0, (BATTERY_CAPACITY_KWH * (battery_soc / 100.0)) - (BATTERY_CAPACITY_KWH * (green_target_soc / 100.0)))

        # Morgen-salg: Estimat af volumen. Hvis vi sælger til aften, falder vi til green_target_soc. Ellers falder vi fra nuværende.
        expected_soc_before_morning = green_target_soc if available_sell_kwh_evening > 0 else battery_soc
        # Fratræk et groft estimat for nattens forbrug (f.eks. 15% af kapaciteten) for et mere retvisende time-estimat
        expected_soc_before_morning = max(min_soc_val, expected_soc_before_morning - 15.0)

        available_sell_kwh_morning = max(0.0, (BATTERY_CAPACITY_KWH * (expected_soc_before_morning / 100.0)) - (BATTERY_CAPACITY_KWH * (min_soc_val / 100.0)))

        hours_needed_morning = max(1, math.ceil(available_sell_kwh_morning / (MAX_DISCHARGE_W / 1000.0)))
        hours_needed_evening = max(1, math.ceil(available_sell_kwh_evening / (MAX_DISCHARGE_W / 1000.0)))

        # Extract future prices to find exact peak times and thresholds
        future_prices_today = [{'time': datetime.strptime(k, "%Y-%m-%d %H"), 'price': v} for k, v in sell_dict.items() if current_hour <= datetime.strptime(k, "%Y-%m-%d %H") < now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)]

        # Find next upcoming morning window (06:00 to 11:59)
        morning_start = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if now.hour >= 12:
            morning_start += timedelta(days=1)
        morning_end = morning_start.replace(hour=12)

        future_prices_morning = [{'time': datetime.strptime(k, "%Y-%m-%d %H"), 'price': v} for k, v in sell_dict.items() if morning_start <= datetime.strptime(k, "%Y-%m-%d %H") < morning_end]

        max_evening_peak = 0.0
        evening_peak_time = "N/A"
        evening_threshold = 0.0

        if future_prices_today:
            sorted_evening = sorted(future_prices_today, key=lambda x: x['price'], reverse=True)
            max_evening_peak = sorted_evening[0]['price']
            evening_peak_time = sorted_evening[0]['time'].strftime("%H:%M")
            evening_threshold = sorted_evening[min(hours_needed_evening, len(sorted_evening)) - 1]['price']

        max_morning_peak = 0.0
        morning_peak_time = "N/A"
        morning_threshold = 0.0

        if future_prices_morning:
            sorted_morning = sorted(future_prices_morning, key=lambda x: x['price'], reverse=True)
            max_morning_peak = sorted_morning[0]['price']
            morning_peak_time = sorted_morning[0]['time'].strftime("%H:%M")
            morning_threshold = sorted_morning[min(hours_needed_morning, len(sorted_morning)) - 1]['price']

        print(f"DEBUG: Peak-Finder [Morning]: Max {max_morning_peak:.2f} @ {morning_peak_time}. Needs {hours_needed_morning}h to sell volume. Threshold: {morning_threshold:.2f}")
        print(f"DEBUG: Peak-Finder [Evening]: Max {max_evening_peak:.2f} @ {evening_peak_time}. Needs {hours_needed_evening}h to sell volume. Threshold: {evening_threshold:.2f}")
        # --- AI STRATEGY SELECTION (PRIORITY RANKING) ---
        if is_tvangsladning_now:
            handling = get_msg("tvangsladning", pris=price_now_inc)
            target_mode = "Time of use"
            target_charge = MAX_CHARGE_W
            action_id = 10

        elif is_pre_dump_now:
            handling = get_msg("pre_dump", tid=first_neg_time.strftime("%H:00"))
            target_mode = "Custom"
            target_discharge = MAX_DISCHARGE_W
            action_id = 11

        elif ev_shield_triggered:
            handling = ev_msg
            target_mode = "Custom"
            target_discharge = ev_dynamic_discharge
            target_charge = MAX_CHARGE_W
            action_id = 9

        elif valgt_profil == "Backup Mode":
            if price_now_ex < min_export_price and ((pv_w - p1_w - batt_w) > 100 or (is_currently_export_stopped and pv_w > 50)):
                handling = get_msg("export_stop")
                action_id = 2
                target_mode = "Self-consumption"
                if battery_soc < 50:
                    target_mode = "Custom"
                    target_charge = MAX_CHARGE_W
            else:
                handling = get_msg("backup_mode")
                action_id = 6
                if battery_soc < 50:
                    target_mode = "Custom"
                    target_charge = MAX_CHARGE_W

        elif valgt_profil == "Smart Selvforsyning":
            if price_now_ex < min_export_price and ((pv_w - p1_w - batt_w) > 100 or (is_currently_export_stopped and pv_w > 50)):
                handling = get_msg("export_stop_limit", limit=min_export_price)
                action_id = 2
                target_mode = "Self-consumption"
                if battery_soc < 90:
                    target_charge = MAX_CHARGE_W

            elif 6 <= now.hour <= 11 and price_now_ex >= total_sell_barrier and price_now_ex >= green_min_sell_price and sol_faktor >= bruger_sol_faktor and (battery_soc >= (min_soc_val + 5.0) or (is_currently_selling and battery_soc >= min_soc_val)):

                # Sell to bottom (min_soc_val) using dynamic volume threshold
                if price_now_ex >= (morning_threshold * 0.98):
                    handling = get_msg("smart_sell_morning", soc=int(min_soc_val))
                    target_mode = "Custom"
                    target_discharge = MAX_DISCHARGE_W
                    action_id = 4

            elif price_now_ex >= total_sell_barrier and price_now_ex >= green_min_sell_price and (battery_soc >= (green_target_soc + salgs_buffer) or (is_currently_selling and battery_soc >= green_target_soc)):

                # Sell surplus down to safe night survival limit using dynamic volume threshold
                # Only sell in evening if evening peak is greater than or equal to morning peak
                if price_now_ex >= (evening_threshold * 0.98) and max_evening_peak >= max_morning_peak:
                    handling = get_msg("smart_sell_evening", soc=int(green_target_soc))
                    target_mode = "Custom"
                    target_discharge = MAX_DISCHARGE_W
                    action_id = 4

            elif is_now_cheapest and (now.hour < 6 or now.hour >= 23):
                handling = get_msg("smart_charge_night", w=smart_night_charge_w)
                target_mode = "Time of use"
                target_charge = smart_night_charge_w
                action_id = 5

            elif is_now_cheapest_afternoon and 6 <= now.hour < 17:
                handling = get_msg("tarif_buster", w=smart_afternoon_charge_w)
                target_mode = "Time of use"
                target_charge = smart_afternoon_charge_w
                action_id = 8

            elif is_daytime and battery_soc < 98.0:
                future_sell_prices = [v for k, v in sell_dict.items() if now.strftime("%Y-%m-%d") in k and int(k.split()[-1]) <= 17 and datetime.strptime(k, "%Y-%m-%d %H") > current_hour]
                cheapest_sell_later = min(future_sell_prices) if future_sell_prices else price_now_ex

                # Check for significant price drop (dynamic value) or hitting safety price
                # Check for significant price drop (must drop more than user setting, or drop below 0)
                # Check for significant price drop (must drop more than user setting, or drop below 0), restricted to 06:00 - 12:00
                expecting_price_drop = (price_now_ex > cheapest_sell_later) and ((price_now_ex - cheapest_sell_later) > throttle_pris_dyk or cheapest_sell_later < 0.0) and (6 <= now.hour <= 12)

                # Calculate pure surplus solar forecast until 17:00
                expected_surplus_later_kwh = 0.0
                for i in range(1, 17 - now.hour):
                    future_hour = now + timedelta(hours=i)
                    key_f = future_hour.strftime("%Y-%m-%d %H")
                    sol_f = solar_dict.get(key_f, 0.0)

                    load_f_w = ml_predictions_w.get(key_f, 0.0)

                    surplus_f = max(0.0, sol_f - (load_f_w / 1000.0))
                    expected_surplus_later_kwh += surplus_f

                missing_to_full_kwh = BATTERY_CAPACITY_KWH * ((100.0 - battery_soc) / 100.0)
                forecast_allows_throttling = expected_surplus_later_kwh >= (missing_to_full_kwh * 1.1)

                # Check if throttle is currently locked due to low battery
                is_throttle_paused_soc = False
                if battery_soc < throttle_min_soc:
                    is_throttle_paused_soc = True
                elif battery_soc < throttle_hysteresis_target and "Batteri under grænse" in current_plan_state:
                    is_throttle_paused_soc = True

                should_throttle = (expecting_price_drop and forecast_allows_throttling) or is_peak_shaving

                if should_throttle:
                    if naked_house_w > pv_w:
                        # 🔴 SAFETY NET: Cloud cover or high load! Pause throttle and run Self-consumption
                        handling = "🌤️ Sol-Throttling Pauset: Forbrug overstiger sol. Skifter til Self-consumption."
                        target_mode = "Self-consumption"
                        target_charge = 10000
                        target_discharge = MAX_DISCHARGE_W
                        action_id = 1
                    elif is_throttle_paused_soc:
                        # 🔴 SAFETY NET: Avoid yo-yo effect. Battery is too low to throttle.
                        handling = f"🌤️ Sol-Throttling Pauset: Batteri under grænse ({battery_soc:.1f}%). Lader op til {throttle_hysteresis_target:.1f}%..."
                        target_mode = "Self-consumption"
                        target_charge = 10000
                        target_discharge = MAX_DISCHARGE_W
                        action_id = 1
                    else:
                        # Safe to proceed: Run throttle via Custom Mode
                        # Alt er trygt: Kør throttle via Custom Mode
                        if is_peak_shaving:
                            handling = f"🌤️ Sol-Throttling (Peak Shaving): Udsætter opladning til 12kW-peak. Limit: {smart_solar_charge_w}W."
                            target_charge = smart_solar_charge_w
                        else:
                            handling = f"🌤️ Intelligent Sol-Throttle: Sælger nu ({price_now_ex:.2f} kr). Venter på {cheapest_sell_later:.2f} kr. Solprognose: +{expected_surplus_later_kwh:.1f} kWh."
                            target_charge = 0  # Force 0W charge to maximize export

                        target_mode = "Custom"
                        target_discharge = int(naked_house_w + 300)
                        action_id = 3
                else:
                    if not forecast_allows_throttling and expecting_price_drop:
                        handling = f"🚀 Normal Drift: Prognose svag (+{expected_surplus_later_kwh:.1f} kWh). Sikrer fyldt batteri fremfor throttle."
                    elif not expecting_price_drop and not is_peak_shaving:
                        handling = get_msg("normal_steady")
                    elif smart_solar_charge_w >= 9000:
                        handling = get_msg("normal_busy")
                    else:
                        handling = get_msg("normal_low_price", pris=price_now_ex)

        elif valgt_profil == "Profit Mode":
            if price_now_ex < min_export_price and ((pv_w - p1_w - batt_w) > 100 or (is_currently_export_stopped and pv_w > 50)):
                handling = get_msg("export_stop")
                action_id = 2
                target_mode = "Self-consumption"
            elif price_now_ex >= (red_profit_margin + total_sell_barrier) and (battery_soc >= (min_soc_val + 5.0) or (is_currently_selling and battery_soc >= min_soc_val)):

                # PROFIT LOOK-AHEAD: Er dette døgnets absolut højeste pris fremefter?
                future_profit_prices = [v for k, v in sell_dict.items() if now.strftime("%Y-%m-%d") in k and int(k.split()[-1]) >= now.hour]
                max_profit_price = max(future_profit_prices) if future_profit_prices else price_now_ex

                if price_now_ex >= (max_profit_price * 0.95):
                    handling = get_msg("profit_arbitrage", soc=int(min_soc_val))
                    target_mode = "Custom"
                    target_discharge = MAX_DISCHARGE_W
                    action_id = 4
            elif is_now_cheapest:
                handling = get_msg("profit_charge")
                target_mode = "Time of use"
                target_charge = smart_night_charge_w
                action_id = 5
            else:
                target_mode = "Self-consumption"
                action_id = 1

        # =====================================================================
        # AI PROFIT TRACKER (THE PIGGY BANK)
        # =====================================================================
        profit_data = load_ai_profit()

        # Nulstil "I dag" hvis vi har krydset midnat
        if profit_data["date"] != now.strftime("%Y-%m-%d"):
            profit_data["today"] = 0.0
            profit_data["date"] = now.strftime("%Y-%m-%d")

        # Hvis vi bevidst sælger ud af batteriet for profit lige nu (Action 4 eller 11)
        if action_id in [4, 11] and p1_w < -100:
            # Scriptet sover i 3 minutter af gangen (3 min = 0.05 timer)
            timer_gaaet = 0.05
            # P1_w er negativ når vi eksporterer, så vi bruger abs()
            kwh_solgt = (abs(p1_w) / 1000.0) * timer_gaaet

            # Profit = Salgspris - Genkøbspris (den billigste fremtidige natpris) - Batterislitage
            profit_margin = price_now_ex - min_future_buy_price - degradation_price

            if profit_margin > 0:
                tjent_lige_nu = kwh_solgt * profit_margin
                profit_data["today"] += tjent_lige_nu
                profit_data["total"] += tjent_lige_nu
                save_ai_profit(profit_data)

        # --- SIMULATION (CRYSTAL BALL) ---
        sim_soc = battery_soc
        sim_soc_list = []
        sim_time_list = []
        sim_throttle_paused_soc = False
        sim_charge_hours = []
        sim_arbitrage_hours = []
        sim_load_list = []
        sim_net_list = []
        sim_solar_list = []
        sim_real_solar_list = []

        max_soc_drop_per_hour = ((MAX_DISCHARGE_W / 1000.0) / BATTERY_CAPACITY_KWH) * 100.0

        for i in range(1, 25):
            future = now + timedelta(hours=i)
            key = future.strftime("%Y-%m-%d %H")
            solar_kwh = solar_dict.get(key, 0.0)
            sim_solar_list.append(solar_kwh * 1000.0)

            temp_guess = weather_dict.get(key, 10.0)
            sim_max_charge_w = find_charge_experience(battery_experience_now, temp_guess, sim_soc)
            sim_max_soc_charge_per_hour = ((sim_max_charge_w / 1000.0) / BATTERY_CAPACITY_KWH) * 100.0

            load_kwh = ml_predictions_w.get(key, 0.0) / 1000.0
            sim_load_list.append(load_kwh * 1000.0)

            net_kwh = solar_kwh - load_kwh
            sim_net_list.append(net_kwh)

            t_price_sell = sell_dict.get(key, 0.0)
            t_price_buy = buy_dict.get(key, 0.0)

            if t_price_sell < min_export_price:
                room_in_battery_w = max(0.0, BATTERY_CAPACITY_KWH * ((100.0 - sim_soc) / 100.0)) * 1000.0
                max_possible_charge = min(MAX_CHARGE_W, room_in_battery_w)
                limited_solar_w = min(solar_kwh * 1000.0, (load_kwh * 1000.0) + max_possible_charge)
                sim_real_solar_list.append(limited_solar_w)
            else:
                sim_real_solar_list.append(solar_kwh * 1000.0)

            is_charge_hour = False
            is_afternoon_charge = False

            # Tjek eftermiddagsladning (Tarif-Buster) først for dagtimer
            if 6 <= future.hour < 17:
                for bt in selected_afternoon_hours:
                    if bt.hour == future.hour and bt.day == future.day:
                        if sim_soc < 99.0:
                            is_charge_hour = True
                            is_afternoon_charge = True
                            sim_charge_hours.append(key)
                        break

            # Tjek natladning for nattetimer
            if not is_charge_hour and (future.hour < 6 or future.hour >= 23):
                for bt in selected_charge_hours:
                    if bt.hour == future.hour and bt.day == future.day:
                        if sim_soc < night_target_soc:
                            is_charge_hour = True
                            sim_charge_hours.append(key)
                        break

            is_arbitrage_hour = False

            # Find the highest 15-minute peak within this specific future hour
            hour_max_peak = get_max_peak_in_window(future.replace(minute=0, second=0, microsecond=0), 1, sell_dict)

            if valgt_profil == "Profit Mode":
                if hour_max_peak >= (red_profit_margin + total_sell_barrier) and sim_soc >= (min_soc_val + 5.0):
                    hours_left_today = max(1, 24 - future.hour)
                    max_profit_price_sim = get_max_peak_in_window(future.replace(minute=0, second=0, microsecond=0), hours_left_today, sell_dict)
                    if hour_max_peak >= (max_profit_price_sim - 0.01):
                        is_arbitrage_hour = True

            elif valgt_profil == "Smart Selvforsyning":
                if 6 <= future.hour <= 11 and sol_faktor >= bruger_sol_faktor and sim_soc >= (min_soc_val + 5.0):
                    if hour_max_peak >= total_sell_barrier and hour_max_peak >= green_min_sell_price:
                        if hour_max_peak >= (morning_threshold * 0.98):
                            is_arbitrage_hour = True

                elif sim_soc >= (green_target_soc + salgs_buffer):
                    if hour_max_peak >= total_sell_barrier and hour_max_peak >= green_min_sell_price:
                        # Prevent simulated evening arbitrage if morning peak is higher
                        if hour_max_peak >= (evening_threshold * 0.98) and max_evening_peak >= max_morning_peak:
                            is_arbitrage_hour = True
            if is_arbitrage_hour:
                sim_arbitrage_hours.append(key)

            if is_charge_hour:
                if is_afternoon_charge:
                    # Eftermiddags-opladning ignorerer nat-målet og bruger den udregnede watt-styrke
                    charge_kwh = smart_afternoon_charge_w / 1000.0
                    actual_max_kwh = sim_max_charge_w / 1000.0
                    room_kwh = ((100.0 - sim_soc) / 100.0) * BATTERY_CAPACITY_KWH
                    charge_kwh = min(charge_kwh, actual_max_kwh, room_kwh)
                    sim_soc += ((charge_kwh + net_kwh) / BATTERY_CAPACITY_KWH) * 100.0
                else:
                    # Nat-opladning rammer night_target_soc præcist
                    missing_soc = max(0, night_target_soc - sim_soc)
                    missing_kwh = (missing_soc / 100.0) * BATTERY_CAPACITY_KWH
                    actual_max_kwh = sim_max_charge_w / 1000.0
                    charge_kwh = min(missing_kwh, actual_max_kwh)
                    sim_soc += ((charge_kwh + net_kwh) / BATTERY_CAPACITY_KWH) * 100.0

            elif is_arbitrage_hour:
                if valgt_profil == "Profit Mode" or (valgt_profil == "Smart Selvforsyning" and 6 <= future.hour <= 11):
                    ideal_target_soc = min_soc_val
                else:
                    ideal_target_soc = green_target_soc

                # STRAMNING: Vi dumper så meget som inverteren FYSISK kan på en time,
                # i stedet for kun at sælge ned til en kunstig 'realistic' grænse.
                available_dump_kwh = max(0.0, ((sim_soc - ideal_target_soc) / 100.0) * BATTERY_CAPACITY_KWH)
                actual_dump_kwh = min(available_dump_kwh, MAX_DISCHARGE_W / 1000.0)

                sim_soc -= (actual_dump_kwh / BATTERY_CAPACITY_KWH) * 100.0
                sim_soc += (net_kwh / BATTERY_CAPACITY_KWH) * 100.0
                sim_soc = max(ideal_target_soc, sim_soc) # Sørg for, vi aldrig borer under målet

            else:
                if net_kwh > 0:
                    t_solar_w_check = solar_dict.get(key, 0.0) * 1000.0
                    is_daytime_sim = t_solar_w_check > 100.0 or (6 <= future.hour <= 18)

                    future_sell_prices_sim = [v for k, v in sell_dict.items() if future.strftime("%Y-%m-%d") in k and int(k.split()[-1]) <= 17 and datetime.strptime(k, "%Y-%m-%d %H") > future]
                    cheapest_sell_later_sim = min(future_sell_prices_sim) if future_sell_prices_sim else t_price_sell
                    expecting_price_drop_sim = cheapest_sell_later_sim < throttle_safety_price

                    missing_to_full_kwh_sim = BATTERY_CAPACITY_KWH * ((100.0 - sim_soc) / 100.0)

                    # --- PEAK SHAVING MED SOL-LÅS ---
                    today_solar_hours_sim = [v for k, v in solar_dict.items() if k.startswith(future.strftime("%Y-%m-%d"))]
                    max_predicted_solar_w_sim = max(today_solar_hours_sim) * 1000.0 if today_solar_hours_sim else 0.0
                    rest_solar_today_kwh_sim = sum([v for k, v in solar_dict.items() if k.startswith(future.strftime("%Y-%m-%d")) and future.hour <= int(k.split()[-1]) <= 18])

                    is_peak_shaving_sim = False

                    # Her bruger vi nu 'sol_laas_threshold' dynamisk i stedet for det hårde 40.0 tal!
                    if max_predicted_solar_w_sim >= 12000.0 and rest_solar_today_kwh_sim > (missing_to_full_kwh_sim * 1.5) and future.hour < 11 and sim_soc >= sol_laas_threshold:
                        smart_solar_charge_w_sim = 0
                        is_peak_shaving_sim = True
                    else:
                        cheap_solar_kwh_sim = sum([v for k, v in solar_dict.items() if k.startswith(future.strftime("%Y-%m-%d")) and int(k.split()[-1]) >= future.hour and sell_dict.get(k, 99.0) < throttle_safety_price])
                        expected_cheap_fill_sim = cheap_solar_kwh_sim * (throttle_aggression / 10.0)
                        rest_need_now_kwh_sim = max(0.5, missing_to_full_kwh_sim - expected_cheap_fill_sim)

                        hours_with_solar_left_sim = max(1, 17 - future.hour)
                        ideal_solar_w_sim = (rest_need_now_kwh_sim / hours_with_solar_left_sim) * 1000.0
                        smart_solar_charge_w_sim = int(max(200, min(MAX_CHARGE_W, ideal_solar_w_sim)))

                    # Track hysteresis state in simulation
                    if sim_soc < throttle_min_soc:
                        sim_throttle_paused_soc = True
                    elif sim_soc >= throttle_hysteresis_target:
                        sim_throttle_paused_soc = False

                    should_throttle_sim = (expecting_price_drop_sim or is_peak_shaving_sim) and smart_solar_charge_w_sim < 9000 and sim_soc < 98.0 and not sim_throttle_paused_soc

                    if t_price_sell < min_export_price:
                        sim_soc += min(sim_max_soc_charge_per_hour, (net_kwh / BATTERY_CAPACITY_KWH) * 100.0)
                    elif is_daytime_sim and sol_faktor >= bruger_sol_faktor:
                        if not should_throttle_sim:
                            sim_soc += min(sim_max_soc_charge_per_hour, (net_kwh / BATTERY_CAPACITY_KWH) * 100.0)
                        else:
                            actual_charge_kwh = min(net_kwh, smart_solar_charge_w_sim / 1000.0)
                            sim_soc += (actual_charge_kwh / BATTERY_CAPACITY_KWH) * 100.0
                    else:
                        sim_soc += min(sim_max_soc_charge_per_hour, (net_kwh / BATTERY_CAPACITY_KWH) * 100.0)
                else:
                    actual_draw_kwh = max(net_kwh, -(MAX_DISCHARGE_W / 1000.0))
                    sim_soc += (actual_draw_kwh / BATTERY_CAPACITY_KWH) * 100.0

            sim_soc = max(min_soc_val, min(100.0, sim_soc))
            sim_time_list.append(key)
            sim_soc_list.append(round(sim_soc, 1))

        # --- COMPILE DATA FOR CSV LOGGING ---
        log_entry = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "profil": valgt_profil,
            "batteri_soc": battery_soc,
            "pris_koeb_inkl_moms": price_now_inc,
            "pris_salg_ex_moms": price_now_ex,
            "sol_prognose_nu_w": solar_forecast_now,
            "sol_rest_idag_kwh": solar_expected,
            "sol_faktor_prognose": round(sol_faktor, 2),
            "hus_forbrug_nu_w": naked_house_w,
            "pv_produktion_nu_w": pv_w,
            "p1_grid_nu_w": p1_w,
            "batteri_watt_nu": batt_w,
            "ev_forbrug_total_w": ev_total_w,
            "throttle_safety_price": throttle_safety_price,
            "min_eksport_pris_limit": min_export_price,
            "action_id": action_id,
            "target_mode": target_mode,
            "target_charge_w": target_charge,
            "beslutning_tekst": handling,
            "udendoers_temp": current_temp
        }
        save_to_csv(log_entry)

        print(get_msg("action_sent", handling=handling))

        # =====================================================================
        # RECORD CURRENT DECISION TO 48H ROLLING LOG
        # =====================================================================
        debug_mode = get_ha_state("input_boolean.ai_debug_mode", "text") == "on"
        current_hour_key = now.strftime("%Y-%m-%d %H")
        prev_plan = rolling_data.get("planned_schedule", {}).get(current_hour_key, "Ikke registreret")

        rolling_data["history"][current_hour_key] = {
            "hour_key": current_hour_key,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "pris_koeb_inkl_moms": round(price_now_inc, 2),
            "pris_salg_ex_moms": round(price_now_ex, 2),
            "batteri_soc": round(battery_soc, 1),
            "sol_w": int(pv_w),
            "forbrug_w": int(naked_house_w),
            "action_id": action_id,
            "target_mode": target_mode,
            "target_charge_w": target_charge,
            "beslutning_tekst": handling,
            "tidligere_planlagt": prev_plan
        }

        headers = {"Authorization": f"Bearer {HA_TOKEN}", "content-type": "application/json"}
        payload = {
            "state": handling,
            "attributes": {
                "friendly_name": "Intelligent Solcellestyring (ML)",
                "version": "1.0.0",
                "icon": "mdi:solar-power" if valgt_profil == "Smart Selvforsyning" else ("mdi:cash" if valgt_profil == "Profit Mode" else "mdi:shield-home"),
                "sidst_opdateret": now.strftime("%Y-%m-%d %H:%M:%S"),
                "target_work_mode": target_mode,
                "target_battery_input_power": target_charge,
                "target_battery_output_power": target_discharge,
                "action_id": action_id,
                "ml_expected_load_w": round(naked_house_w, 0),
                "calc_true_capacity_kwh": round(BATTERY_CAPACITY_KWH, 2),
                "slitagepris_kr_kwh": round(degradation_price, 2),
                "ai_profit_today": round(profit_data["today"], 2),
                "ai_profit_total": round(profit_data["total"], 2),
                "current_buy_price": round(price_now_inc, 2),
                "current_sell_price": round(price_now_ex, 2),
                "model_sidst_traenet": model_sidst_traenet,
                "sim_times": sim_time_list,
                "sim_soc": sim_soc_list,
                "sim_forbrug_w": [int(f) for f in sim_load_list],
                "sim_sol_w": [int(s) for s in sim_solar_list],
                "sim_real_sol_w": [int(s) for s in sim_real_solar_list]
            }
        }

        print(get_msg("forecast_header"))

        for i in range(1, 25):
            future = now + timedelta(hours=i)
            key = future.strftime("%Y-%m-%d %H")
            b_price = buy_dict.get(key, 0.0)
            s_price = sell_dict.get(key, 0.0)

            is_charge_hour_future = key in sim_charge_hours
            is_arbitrage_hour_future = key in sim_arbitrage_hours

            time_soc = sim_soc_list[i-1]
            time_load = sim_load_list[i-1]
            time_net = sim_net_list[i-1]
            t_temp = weather_dict.get(key, 10.0)
            t_solar_w = int(solar_dict.get(key, 0.0) * 1000)
            t_net_w = int(time_net * 1000)

            prev_soc = sim_soc_list[i-2] if i > 1 else battery_soc

            # --- NYT YDMYGHEDS-TJEK START ---
            if is_arbitrage_hour_future:
                hus_brug_pct = (abs(time_net) / BATTERY_CAPACITY_KWH) * 100.0 if time_net < 0 else 0.0
                fald_pct = prev_soc - time_soc
                # Hvis faldet i batteriet er mindre end eller lig med det huset slugte, så eksporterede vi intet.
                if time_net < 0 and fald_pct <= (hus_brug_pct + 0.5):
                    is_arbitrage_hour_future = False # Aflys praleriet!
            # --- NYT YDMYGHEDS-TJEK SLUT ---

            soc_text = f"🔋 {int(prev_soc):2d}%"

            # Sikkerhedsnet: Defineres altid!
            plan_text = "Ukendt handling"

            def dbg_txt(id_n):
                return f" [ID: {id_n} | ☀️ {t_solar_w}W]" if debug_mode else ""

            if is_charge_hour_future:
                is_aft_plan = key in [bt.strftime("%Y-%m-%d %H") for bt in selected_afternoon_hours]
                if is_aft_plan:
                    plan_text = f"{soc_text}{dbg_txt(8)} " + get_msg("tarif_buster", w=smart_afternoon_charge_w)
                else:
                    plan_text = f"{soc_text}{dbg_txt(5)} " + get_msg("plan_charge")
            elif is_arbitrage_hour_future:
                end_soc = int(time_soc)
                if valgt_profil == "Profit Mode":
                    profit = s_price - min_future_buy_price
                    plan_text = f"{soc_text}{dbg_txt(4)} " + get_msg("plan_profit", profit=profit) + get_msg("plan_down_to", soc=end_soc)
                elif 6 <= future.hour <= 11:
                    # Dette griber Smart Selvforsyning (Morgen)
                    plan_text = f"{soc_text}{dbg_txt(4)} " + get_msg("plan_morning") + get_msg("plan_down_to", soc=end_soc)
                else:
                    # Dette griber Smart Selvforsyning (Aften)
                    plan_text = f"{soc_text}{dbg_txt(4)} " + get_msg("plan_evening") + get_msg("plan_down_to", soc=end_soc)
            elif time_net > 0.0:
                if s_price < min_export_price:
                    plan_text = f"{soc_text}{dbg_txt(2)} " + get_msg("plan_stop")
                elif time_soc >= 99.0:
                    plan_text = f"{soc_text}{dbg_txt(1)} " + get_msg("plan_export")
                elif (t_solar_w > 100 or (6 <= future.hour <= 18)) and sol_faktor >= bruger_sol_faktor:
                    future_sell_prices_sim = [v for k_s, v in sell_dict.items() if future.strftime("%Y-%m-%d") in k_s and int(k_s.split()[-1]) <= 17 and datetime.strptime(k_s, "%Y-%m-%d %H") > future]
                    cheapest_sell_later_sim = min(future_sell_prices_sim) if future_sell_prices_sim else s_price
                    expecting_price_drop_sim = (s_price > cheapest_sell_later_sim) and ((s_price - cheapest_sell_later_sim) > throttle_pris_dyk or cheapest_sell_later_sim < 0.0) and (6 <= future.hour <= 12)

                    expected_surplus_later_kwh_sim = 0.0
                    for j in range(1, 17 - future.hour):
                        future_hour_sim = future + timedelta(hours=j)
                        key_f_sim = future_hour_sim.strftime("%Y-%m-%d %H")
                        sol_f_sim = solar_dict.get(key_f_sim, 0.0)

                        load_f_w_sim = ml_predictions_w.get(key_f_sim, 0.0)

                        surplus_f_sim = max(0.0, sol_f_sim - (load_f_w_sim / 1000.0))
                        expected_surplus_later_kwh_sim += surplus_f_sim

                    missing_to_full_kwh_sim = BATTERY_CAPACITY_KWH * ((100.0 - time_soc) / 100.0)
                    forecast_allows_throttling_sim = expected_surplus_later_kwh_sim >= (missing_to_full_kwh_sim * 1.1)

                    should_throttle_sim = (expecting_price_drop_sim and forecast_allows_throttling_sim and time_soc < 98.0)

                    if should_throttle_sim:
                        charging_w = 0  # Simulation of 0W charge during throttling
                        plan_text = f"{soc_text}{dbg_txt(3)} 🌤️ Sol-Throttle (Prognose: OK)"
                    else:
                        if not forecast_allows_throttling_sim and expecting_price_drop_sim and time_soc < 98.0:
                            plan_text = f"{soc_text}{dbg_txt(1)} 🚀 Lader (Prognose: Svag)"
                        else:
                            plan_text = f"{soc_text}{dbg_txt(1)} " + get_msg("plan_normal")
                else:
                    plan_text = f"{soc_text}{dbg_txt(1)} " + get_msg("plan_sun_charge")
            else:
                prev_soc = sim_soc_list[i-2] if i > 1 else battery_soc
                if (prev_soc - time_soc) > 0.5:
                    plan_text = f"{soc_text}{dbg_txt(1)} " + get_msg("plan_batt_cover", w=abs(t_net_w))
                else:
                    plan_text = f"{soc_text}{dbg_txt(1)} " + get_msg("plan_grid_cover", w=int(time_load))

            payload["attributes"][f"plan_{i}h"] = f"**[K:{b_price:.2f} S:{s_price:.2f}]** {plan_text}"
            rolling_data["planned_schedule"][key] = plan_text
            print(f"{key:<14} | K:{b_price:>4.2f} S:{s_price:>4.2f} | {t_temp:>4.1f}°C | {t_solar_w:>5} W | {int(time_load):>8} W | {t_net_w:>6} W | {time_soc:>4.1f}% | {plan_text}  ")

        # Prune older than 48 hours and save rolling log
        cutoff = now - timedelta(hours=48)
        cutoff_key = cutoff.strftime("%Y-%m-%d %H")
        rolling_data["history"] = {k: v for k, v in rolling_data["history"].items() if k >= cutoff_key}
        rolling_data["planned_schedule"] = {k: v for k, v in rolling_data["planned_schedule"].items() if k >= cutoff_key}
        save_rolling_log(rolling_data)

        # Build 48h rolling history attributes & markdown table
        md_lines = [
            "| Tid | K/S Pris | Batt | Sol / Forbrug | Planlagt | Udført |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        for h in range(1, 49):
            h_time = now - timedelta(hours=h)
            h_key = h_time.strftime("%Y-%m-%d %H")
            if h_key in rolling_data["history"]:
                he = rolling_data["history"][h_key]
                plan_str = he.get('tidligere_planlagt', '-')
                if not plan_str or plan_str == "Ikke registreret":
                    plan_clean = "-"
                else:
                    plan_clean = plan_str.split(" [ID:")[0].strip() if " [ID:" in plan_str else plan_str.strip()

                plan_tag = f" [Plan: {plan_clean}]" if plan_clean != "-" else ""
                
                # Single attribute format (e.g. historik_1h, historik_2h ... historik_48h)
                payload["attributes"][f"historik_{h}h"] = (
                    f"**[{h_time.strftime('%d/%m %H:00')} | K:{he['pris_koeb_inkl_moms']:.2f} S:{he['pris_salg_ex_moms']:.2f}]** "
                    f"🔋 {int(he['batteri_soc'])}% [ID: {he['action_id']} | ☀️ {he['sol_w']}W] ⏪ {he['beslutning_tekst']}{plan_tag}"
                )

                # Markdown table row
                t_str = h_time.strftime("%d/%m %H:00")
                p_str = f"{he['pris_koeb_inkl_moms']:.2f} / {he['pris_salg_ex_moms']:.2f}"
                b_str = f"🔋 {int(he['batteri_soc'])}%"
                pw_str = f"☀️{he['sol_w']}W / 🔌{he['forbrug_w']}W"
                act_str = he['beslutning_tekst']
                if len(act_str) > 42:
                    act_str = act_str[:40] + "..."
                md_lines.append(f"| {t_str} | {p_str} | {b_str} | {pw_str} | {plan_clean} | {act_str} |")
            else:
                payload["attributes"][f"historik_{h}h"] = get_msg("no_history")

        payload["attributes"]["historik_48h_markdown"] = "\n".join(md_lines)

        requests.post(HA_URL, headers=headers, json=payload, timeout=10)

        # =====================================================================
        # LEARNING WATCHDOG: LIVE FEEDBACK FROM BATTERY BMS
        # =====================================================================
        if target_mode == "Time of use" and target_charge >= (MAX_CHARGE_W - 500):
            actual_charge_w = abs(batt_w)
            if actual_charge_w > 200:
                experience = get_battery_experience(NOMINAL_CAPACITY)

                if current_temp >= 10:
                    temp_key = "temp_over_10"
                elif 0 <= current_temp < 10:
                    temp_key = "temp_0_to_10"
                else:
                    temp_key = "temp_under_0"

                if battery_soc < 90:
                    soc_key = "soc_0_to_90"
                else:
                    soc_key = "soc_90_to_100"

                old_value = experience["max_charge_rate"][temp_key][soc_key]
                new_value = int((old_value * 0.8) + (actual_charge_w * 0.2))

                if abs(new_value - old_value) > 50:
                    experience["max_charge_rate"][temp_key][soc_key] = new_value
                    save_battery_experience(experience)
                    print(get_msg("mem_update", temp=temp_key, soc=soc_key, w=new_value))

        print(get_msg("sleep"))

        # Sover i ca. 3 minutter totalt (36 * 5 sekunder), men kigger på knappen konstant
        for _ in range(36):
            time.sleep(5)
            if get_ha_state("input_boolean.trigger_ai_beregning", "text", use_cache=False) == "on":
                print("\n⚡ MANUEL GENBEREGNING AKTIVERET FRA DASHBOARD! Vågner øjeblikkeligt...")
                try:
                    requests.post(f"http://{HA_IP}:{HA_PORT}/api/services/input_boolean/turn_off", headers=headers, json={"entity_id": "input_boolean.trigger_ai_beregning"}, timeout=10)
                except:
                    pass
                break # Bryder loopet og starter forfra med det samme

    except Exception as e:
        print(f"❌ Critical error in main loop: {e}")
        time.sleep(300)
