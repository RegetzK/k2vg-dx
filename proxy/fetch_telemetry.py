#!/usr/bin/env python3
"""
BETA 5 Multi-Mission Telemetry Array
Direct API fetch — no third-party proxies. ZT compliant.
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ─── CONFIG ───────────────────────────────────────────────────────────
STATION_CALL = "K2VG"
MY_GRID = "FM18"
QSO_TOTAL = 124
QSO_CONFIRMED_QRZ = 100
SNR_MIN = -24
SNR_MAX = -15
LAST_SECONDS = 1800  # 30 min window

FICTIONAL_STATIONS = [
    {"call": "NCC-1701", "grid": "GSO-FM18", "band": "ALL", "db": None, "freq": None, "dxcc": "USS ENTERPRISE", "status": "UPLINK ACTIVE", "lore": True},
    {"call": "N/A", "grid": "40 ERIDANI A", "band": "ALL", "db": None, "freq": None, "dxcc": "VULCAN", "status": "MONITORING 🖖", "lore": True},
    {"call": "IC/MIL/GOV COMMS", "grid": "ALL", "band": "ALL", "db": None, "freq": None, "dxcc": "EARTH", "status": "MONITORING", "lore": True},
    {"call": "CIV WEB/DARK WEB/COMMS", "grid": "ALL", "band": "ALL", "db": None, "freq": None, "dxcc": "EARTH", "status": "MONITORING", "lore": True},
]

HEADERS = {"User-Agent": "K2VG-BETA5-Telemetry/1.0"}


# ─── PSKREPORTER ─────────────────────────────────────────────────────
def fetch_psk_telemetry():
    """Direct XML fetch from PSKReporter. No CORS proxies."""
    url = f"https://pskreporter.info/psk/reporter.cfm?call={STATION_CALL}&last={LAST_SECONDS}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()

        root = ET.fromstring(data)
        dx_signals = []

        for report in root.findall("receptionReport"):
            try:
                db_val = int(report.get("sNR", "0"))
                callsign = report.get("receiverCallsign", "Unknown")
                grid = report.get("receiverGrid", "Unknown")
                freq = int(report.get("frequency", "0"))

                if SNR_MIN <= db_val <= SNR_MAX:
                    dx_signals.append({
                        "call": callsign,
                        "grid": grid,
                        "db": db_val,
                        "freq": round(freq / 1000000, 4),
                        "time": "LIVE",
                        "lore": False,
                    })
            except (ValueError, TypeError):
                continue

        return {"status": "ONLINE", "dx_tracks": dx_signals}

    except Exception as e:
        print(f"PSKReporter fetch failed: {e}", file=sys.stderr)
        return {"status": "DEGRADED", "dx_tracks": []}


# ─── NOAA SWPC ───────────────────────────────────────────────────────
def fetch_space_weather():
    """Direct JSON fetch from NOAA SWPC APIs."""
    result = {"sfi": "N/A", "kp": "N/A", "geomag": "N/A", "flare_risk": "N/A"}

    # Kp index
    try:
        req = urllib.request.Request(
            "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
            headers=HEADERS,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            kp_data = json.loads(resp.read())
        if kp_data:
            result["kp"] = str(kp_data[-1].get("kp_index", "N/A"))
            result["geomag"] = "STABLE" if float(kp_data[-1].get("kp_index", 0)) < 4 else "ELEVATED"
    except Exception as e:
        print(f"SWPC Kp fetch failed: {e}", file=sys.stderr)

    # Solar flux (10.7 cm)
    try:
        req = urllib.request.Request(
            "https://services.swpc.noaa.gov/products/solar-cycle-radio-flux.json",
            headers=HEADERS,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            flux_data = json.loads(resp.read())
        if flux_data:
            result["sfi"] = str(flux_data[-1].get("solar_radio_flux", "N/A"))
    except Exception as e:
        print(f"SWPC flux fetch failed: {e}", file=sys.stderr)

    # Space weather summary (for flare risk)
    try:
        req = urllib.request.Request(
            "https://services.swpc.noaa.gov/products/space-weather-summary.json",
            headers=HEADERS,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            swx = json.loads(resp.read())
        if swx:
            result["flare_risk"] = swx[-1].get("radio_blackout", "N/A")
    except Exception as e:
        print(f"SWPC summary fetch failed: {e}", file=sys.stderr)

    return result


# ─── MAIN ────────────────────────────────────────────────────────────
def main():
    print("Initializing BETA 5 Multi-Mission Telemetry Array...")

    solar = fetch_space_weather()
    psk = fetch_psk_telemetry()

    # Merge lore rows + live telemetry
    combined = FICTIONAL_STATIONS + psk["dx_tracks"]

    payload = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "station": {
            "callsign": STATION_CALL,
            "grid": MY_GRID,
            "total_qsos": QSO_TOTAL,
            "confirmed_qrz": QSO_CONFIRMED_QRZ,
        },
        "solar": solar,
        "telemetry": {
            "status": psk["status"],
            "dx_tracks": combined,
        },
    }

    os.makedirs("data", exist_ok=True)
    with open("data/telemetry.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Telemetry written: {len(psk['dx_tracks'])} live signals, status={psk['status']}")


if __name__ == "__main__":
    main()   
