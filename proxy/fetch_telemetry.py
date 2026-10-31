#!/usr/bin/env python3
"""
BETA 5 Multi-Mission Telemetry Array
Direct API fetch — no third-party proxies. ZT compliant.
Uses retrieve.pskreporter.info JSON API per BETA 5 Protocol Section 5A.1.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
import html  # CRITICAL: Added for XSS sanitization

# ─── CONFIG ───────────────────────────────────────────────────────────
STATION_CALL = "K2VG"
MY_GRID = "FM05"  # PATCHED: Corrected from FM18 to FM05
QSO_TOTAL = 124
QSO_CONFIRMED_QRZ = 100
SNR_MIN = -24
SNR_MAX = 24
LAST_SECONDS = 3600  # 1 hour window per BETA 5 Protocol

FICTIONAL_STATIONS = [
    {"call": "NCC-1701", "grid": "GSO-FM05", "band": "ALL", "db": None, "freq": None, "dxcc": "USS ENTERPRISE", "status": "UPLINK ACTIVE", "lore": True},
    {"call": "N/A", "grid": "40 ERIDANI A", "band": "ALL", "db": None, "freq": None, "dxcc": "VULCAN", "status": "MONITORING 🖖", "lore": True},
    {"call": "IC/MIL/GOV COMMS", "grid": "ALL", "band": "ALL", "db": None, "freq": None, "dxcc": "EARTH", "status": "MONITORING", "lore": True},
    {"call": "CIV WEB/DARK WEB/COMMS", "grid": "ALL", "band": "ALL", "db": None, "freq": None, "dxcc": "EARTH", "status": "MONITORING", "lore": True},
]

HEADERS = {"User-Agent": "K2VG-BETA5-Telemetry/1.0"}


def sanitize(text):
    """Escape HTML entities to prevent XSS."""
    if text is None:
        return "N/A"
    return html.escape(str(text))


def band_from_freq(mhz):
    """Convert frequency in MHz to ham band label."""
    if mhz >= 1.8 and mhz < 2: return "160M"
    if mhz >= 3.5 and mhz < 4: return "80M"
    if mhz >= 5.3 and mhz < 5.4: return "60M"
    if mhz >= 7 and mhz < 7.3: return "40M"
    if mhz >= 10.1 and mhz < 10.15: return "30M"
    if mhz >= 14 and mhz < 14.35: return "20M"
    if mhz >= 18 and mhz < 18.16: return "17M"
    if mhz >= 21 and mhz < 21.45: return "15M"
    if mhz >= 24.89 and mhz < 24.99: return "12M"
    if mhz >= 28 and mhz < 29.7: return "10M"
    if mhz >= 50 and mhz < 54: return "6M"
    return f"{mhz:.1f}M"


# ─── PSKREPORTER ─────────────────────────────────────────────────────
def fetch_psk_rx():
    """Fetch spots where K2VG was the RECEIVER (stations K2VG heard)."""
    url = f"https://retrieve.pskreporter.info/query?receiverCallsign={STATION_CALL}&flowStartSeconds=-{LAST_SECONDS}&rptlimit=50&statistics=1"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())

        dx_signals = []
        reports = data.get("receptionReport", [])

        for report in reports:
            try:
                db_val = int(report.get("sNR", "0"))
                callsign = report.get("senderCallsign", "Unknown")
                grid = report.get("senderGrid", "Unknown")
                freq = float(report.get("frequency", "0"))
                freq_mhz = freq / 1_000_000

                if SNR_MIN <= db_val <= SNR_MAX:
                    dx_signals.append({
                        "call": sanitize(callsign),
                        "grid": sanitize(grid),
                        "band": band_from_freq(freq_mhz),
                        "db": db_val,
                        "freq": round(freq_mhz, 4),
                        "time": "LIVE",
                        "lore": False,
                    })
            except (ValueError, TypeError):
                continue

        return dx_signals

    except Exception as e:
        print(f"PSKReporter RX fetch failed: {e}", file=sys.stderr)
        return []


def fetch_psk_tx():
    """Fetch spots where K2VG was the SENDER (stations that heard K2VG)."""
    url = f"https://retrieve.pskreporter.info/query?senderCallsign={STATION_CALL}&flowStartSeconds=-{LAST_SECONDS}&rptlimit=50&statistics=1"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())

        dx_signals = []
        reports = data.get("receptionReport", [])

        for report in reports:
            try:
                db_val = int(report.get("sNR", "0"))
                callsign = report.get("receiverCallsign", "Unknown")
                grid = report.get("receiverGrid", "Unknown")
                freq = float(report.get("frequency", "0"))
                freq_mhz = freq / 1_000_000

                if SNR_MIN <= db_val <= SNR_MAX:
                    dx_signals.append({
                        "call": sanitize(callsign),
                        "grid": sanitize(grid),
                        "band": band_from_freq(freq_mhz),
                        "db": db_val,
                        "freq": round(freq_mhz, 4),
                        "time": "LIVE",
                        "lore": False,
                    })
            except (ValueError, TypeError):
                continue

        return dx_signals

    except Exception as e:
        print(f"PSKReporter TX fetch failed: {e}", file=sys.stderr)
        return []


def fetch_psk_telemetry():
    """Combined RX + TX telemetry from PSKReporter JSON API."""
    rx = fetch_psk_rx()
    tx = fetch_psk_tx()

    # Deduplicate by call+band (keep higher SNR)
    seen = {}
    for sig in rx + tx:
        key = (sig["call"], sig["band"])
        if key not in seen or sig["db"] > seen[key]["db"]:
            seen[key] = sig

    combined = sorted(seen.values(), key=lambda x: x["db"], reverse=True)
    status = "ONLINE" if combined else "DEGRADED"
    return {"status": status, "dx_tracks": combined}


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
            latest = kp_data[-1]
            kp_val = latest.get("kp_index", "N/A")
            result["kp"] = sanitize(str(kp_val))
            try:
                result["geomag"] = "STABLE" if float(kp_val) < 4 else "ELEVATED"
            except (ValueError, TypeError):
                result["geomag"] = "N/A"
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
            latest = flux_data[-1]
            result["sfi"] = sanitize(str(latest.get("solar_radio_flux", "N/A")))
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
            latest = swx[-1]
            result["flare_risk"] = sanitize(latest.get("radio_blackout", "N/A"))
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
