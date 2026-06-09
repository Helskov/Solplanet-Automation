# Solplanet Automation 1.0 ☀️🔋

Solplanet Automation energy management system for Home Assistant. It uses **Machine Learning** to predict your household consumption and real-time spot prices to optimize battery usage. 

Project is my personal project i just chooses to share with other. 
I have only testet with my own Solplanet Hybrid Inverter ASW12KH-T3

Use this at your own risk

Unlike simple "charge-at-night" scripts, this system calculates the **Marginal Cost of Energy** (battery degradation + replacement cost) to ensure that every charge and discharge cycle is financially profitable.

## 🚀 Key Features

- **Machine Learning Forecasts:** Predicts your "naked" house load (excluding EVs) based on history, weather, and day-of-the-week patterns directly from Home Assistant's built-in database (No InfluxDB required!).
- **Universal Solar Forecast Parser:** Automatically translates data from Forecast.Solar, Solcast, Open-Meteo, or Custom ML into standardized predictions.
- **Danish Market Price Support:** Tailored exclusively to the Danish electricity grid with native support for **Strømligning** and **Energi Data Service**. Other integrations (such as Nordpool, Tibber, or ENTSO-E) are explicitly *not* supported.
- **Degradation Awareness:** Calculates battery wear-and-tear in real-time (**DKK/kWh**) to prevent "cycling for pennies."
- **Intelligent Battery Export & Home Protection (Arbitrage):** Automatically discharges stored battery power back to the grid during high-price spikes, but only when the market price guarantees a genuine financial profit after degradation. Crucially, the system calculates a dynamic target reserve, ensuring the battery never over-sells and always retains enough capacity to fully cover your own household consumption during morning and evening peaks.
- **Solar Throttling:** Intelligently sells solar power before price drops to maximize ROI.
- **Dynamic Tariff-Buster:** Automatically pre-charges the battery from the grid before expensive peak hours.
- **Smart Profiles:** Choose between *Smart Self-Consumption*, *Backup Mode*, or *Aggressive Profit (Arbitrage)*.
- **Multi-Language Support:** supports English (EN) and Danish (DA) 

---

## 📋 Prerequisites

Before installing, ensure you have the following ready in Home Assistant:
1. **HACS:** Home Assistant Community Store.
2. **Solplanet / VoltX Inverter Integration:** You **MUST** use the custom integration developed by `calvinbui` via HACS (Supports V2 firmware and schedule slot manipulation). [Link to integration](https://github.com/calvinbui/home-assistant-solplanet)
3. **Custom Frontend Cards (via HACS):** You need to install the following custom Lovelace cards for the dashboard to work and render correctly:
    * `apexcharts-card` (Required for the 24h AI Forecast Crystal Ball)
    * `card-mod` (Required for seamless UI styling and invisible borders)
    * `stack-in-card` (Optional, but recommended for clean vertical stacks)

---

## 🛠️ Installation & Setup

The system is split into two independent parts: The Home Assistant UI/Automations and the Python ML Engine.

### 1. Home Assistant Setup (The UI & Automations)
We use the Home Assistant *Packages* feature to deploy all buttons, sliders, and automations in one go.

1. Choose your preferred language file from the repository (`solplanet_automation_package_en.yaml` or `solplanet_automation_package_da.yaml`).
2. Copy the file into your Home Assistant `/packages/` folder.
3. **CRITICAL STEP:** Open the file in a text editor and use **Find and Replace (Ctrl+F)** to replace the placeholders at the top of the file with your actual entities (e.g., `YOUR_INVERTER_IP_HERE`, `YOUR_DEVICE_ID_HERE`, `YOUR_BATTERY_SOC_SENSOR`).
4. **CONFIGURE RECORDER:** Ensure your Home Assistant database stores enough history for the AI to train on. Open your `configuration.yaml` and add or modify the `recorder` section to keep at least 7-14 days of history (recommend 30 days if your hardware allows):
    ```yaml
    recorder:
      purge_keep_days: 30
    ```
5. Restart Home Assistant to generate all helpers, sensors, automations, and apply the recorder settings.

### 2. Python Engine Setup (The Brain)
It is recommended to run this on the same server/Raspberry Pi hosting your Home Assistant, or any 24/7 Linux machine.

1. Clone this repository and navigate to it.
2. Create a virtual environment and install dependencies:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
3. Create your local config by copying the example: `cp config.ini.example config.ini`.
4. Edit `config.ini` and fill in your details based on your chosen provider layout (see the Configuration Overview table below).
5. **INITIAL ML TRAINING (CRITICAL):** Before starting the live controller, you must train the AI on your historical data to generate the first model. Run:
    ```bash
    python3 python/ml_trainer.py
    ```
    *Wait for the success message confirming that `ml_solcelle_model.pkl` has been created.*

---

## 🧠 24/7 Deployment (Systemd & Cron)

To ensure the automation runs continuously and adapts to your changing habits, set it up as background services.

### 1. Automating the Brain Training (Cronjob)
The ML model needs to learn your consumption patterns. Set it to retrain every night at 03:00 AM.
Open your crontab (`crontab -e`) and add:
```bash
0 3 * * * /path/to/your/Solplanet_Automation/venv/bin/python /path/to/your/Solplanet_Automation/python/ml_trainer.py >> /path/to/your/Solplanet_Automation/trainer.log 2>&1
```

### 2. Running the Live Controller (Systemd)
Create a new service file:
```bash
sudo nano /etc/systemd/system/solplanet.service
```
Paste the following (adjust paths and user!):
```ini
[Unit]
Description=Solplanet AI Controller
After=network.target

[Service]
Type=simple
User=YOUR_LINUX_USERNAME
WorkingDirectory=/path/to/your/Solplanet_Automation
ExecStart=/path/to/your/Solplanet_Automation/venv/bin/python /path/to/your/Solplanet_Automation/python/main_controller.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl enable solplanet.service
sudo systemctl start solplanet.service
```
*(You can monitor the live logs anytime with: `journalctl -u solplanet.service -f`)*

---

## 📊 Dashboard & Visualization

### Main Control Panel
Copy the content of `dashboard_en.yaml` (or `_da.yaml`) into a **Manual Card** in your Home Assistant UI. Remember to use "Find & Replace" to insert your own entity names. This provides the "Faceplate" with profile selection, manual battery sale toggles, and system health.
requirements: 'card-mod' og 'apexcharts-card' via HACS!
### 🔮 Advanced Forecast (The "Crystal Ball")
For the advanced 24-hour visualization, use the code in `forecast_card.yaml` in an **ApexCharts Card**. This visualizes your future SOC, expected house load, and solar production.

---

## 📝 Configuration Overview (`config.ini`)

| Section | Key | Description |
| :--- | :--- | :--- |
| `General` | `LANGUAGE` | `DA` for Danish terminal messages, `EN` for English. |
| `HomeAssistant`| `TRAINING_DAYS` | Number of days of historical data to fetch from HA for AI training (e.g., 7 or 14). |
| `Hardware` | `BATTERY_CAPACITY_KWH` | Physical size of your battery bank (e.g., 20.0). |
| `Hardware` | `MAX_CHARGE_W` | Your inverter's maximum charging/discharging speed in Watts. |
| `Sensors_Core` | `PRICE_BUY` | Core buying price entity. Set to `sensor.stromligning_current_price_vat` for Stromligning, or `sensor.energi_data_service` for Energi Data Service. |
| `Sensors_Core` | `PRICE_SELL` | Live selling spot price entity. Use `sensor.stromligning_spotprice_ex_vat` for Stromligning. **Leave blank** for Energi Data Service to activate internal fallback tariff/VAT stripping logic. |
| `Sensors_Core` | `PRICE_BUY_TOMORROW` | Tomorrow's price validation entity. Use `binary_sensor.stromligning_tomorrow_available_vat` for Stromligning. **Leave blank** for Energi Data Service. |
| `Sensors_EV` | `EV_CHARGERS_W` | Comma-separated list of EV sensors tracking power in Watts (W) to exclude from the core house model. Leave blank if none. |
| `Sensors_EV` | `EV_CHARGERS_KW`| Comma-separated list of EV sensors tracking power in Kilowatts (kW). Leave blank if none. |

---

## ⚠️ Disclaimer
*This project is an advanced open-source automation tool provided "as is". It is used entirely at your own risk (på eget ansvar). Solar battery systems involve high voltage, severe safety risks, and expensive hardware. Always ensure your configuration matches your hardware limits. The developers hold absolutely no liability for drained batteries, financial losses, grid penalties, or hardware degradation.*
