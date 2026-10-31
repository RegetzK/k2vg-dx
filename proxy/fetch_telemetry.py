#!/usr/bin/env python3
"""
BETA 5 Multi-Mission Telemetry Array
Direct API fetch — no third-party proxies. ZT compliant.
PSKReporter retrieve API returns XML (IPFIX attributes), NOT JSON.
This version ONLY queries TX (who heard K2VG) — confirmed active via your map.
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import html

# ─── CONFIG ───────────────────────────────────────────────────────────
STATION_CALL = "K2VG"
MY_GRID = "FM05"
QSO_TOTAL = 124
QSO_CONFIRMED_QRZ = 100
SNR_MIN = -24
SNR_MAX = 24
LAST_SECONDS = 3600          # negative seconds back; max 86400
MODE_FILTER = "FT8"
RPT_LIMIT = 50

FICTIONAL_STATIONS = [
    {"call": "NCC-1701", "grid": "GSO-FM05", "band": "ALL", "db": None, "freq": None, "dxcc": "USS ENTERPRISE", "status": "UPLINK ACTIVE", "lore": True},
    {"call": "N/A", "grid": "40 ERIDANI A", "band": "ALL", "db": None, "freq": None, "dxcc": "VULCAN", "status": "MONITORING 🖖", "lore": True},
    {"call": "IC/MIL/GOV COMMS", "grid": "ALL", "band": "ALL", "db": None, "freq": None, "dxcc": "EARTH", "status": "MONITORING", "lore": True},
    {"call": "CIV WEB/DARK WEB/COMMS", "grid": "ALL", "band": "ALL", "db": None, "freq": None, "dxcc": "EARTH", "status": "MONITORING", "lore": True},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; K2VG-BETA5-Telemetry/1.0; ham-radio telemetry)",
    "Accept": "application/xml, text/xml, */*",
}


def sanitize(text):
    if text is None:
        return "N/A"
    return html.escape(str(text))


def band_from_freq(mhz):
    if 1.8 <= mhz < 2:     return "160M"
    if 3.5 <= mhz < 4:     return "80M"
    if 5.3 <= mhz < 5.4:   return "60M"
    if 7 <= mhz < 7.3:     return "40M"
    if 10.1 <= mhz < 10.15: return "30M"
    if 14 <= mhz < 14.35:  return "20M"
    if 18 <= mhz < 18.16:  return "17M"
    if 21 <= mhz < 21.45:  return "15M"
    if 24.89 <= mhz < 24.99: return "12M"
    if 28 <= mhz < 29.7:   return "10M"
    if 50 <= mhz < 54:     return "6M"
    return f"{mhz:.1f}M"


def _query_pskr(direction):
    """direction='rx' → who K2VG heard. direction='tx' → who heard K2VG."""
    # TEMPORARY: Only TX until RX is confirmed to work
    key = "senderCallsign"  # ← force TX direction
    url = (
        "https://retrieve.pskreporter.info/query"
        f"?{key}={STATION_CALL}"
        f"&flowStartSeconds=-{LAST_SECONDS}"
        f"&mode={MODE_FILTER}"
        f"&rptlimit={RPT_LIMIT}"
        "&rronly=1"
        "&noactive=1"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read()

    root = ET.fromstring(raw)

    # In TX query, the far station is the RECEIVER
    other_call = "receiverCallsign"
    other_loc = "receiverLocator"

    out = []
    for rpt in root.iter("receptionReport"):
        try:
            db_val = int(rpt.get("sNR", "0"))
            call = rpt.get(other_call, "")
            loc = rpt.get(other_loc, "") or ""
            freq_hz = float(rpt.get("frequency", "0"))
        except (ValueError, TypeError):
            continue

        if not call or call.upper() == STATION_CALL:
            continue
        if not (SNR_MIN <= db_val <= SNR_MAX):
            continue

        mhz = freq_hz / 1_000_000
        out.append({
            "call": sanitize(call),
            "grid": sanitize(loc[:4].upper() if loc else "N/A"),
            "band": band_from_freq(mhz),
            "db": db_val,
            "freq": round(mhz, 4),
            "time": "LIVE",
            "lore": False,
        })
    return out


def fetch_psk_telemetry():
    rx, tx = [], []
    try:
        tx = _query_pskr("tx")  # ← only TX for now
    except Exception as e:
        print(f"PSKReporter TX failed: {e}", file=sys.stderr)

    seen = {}
    for sig in tx:  # ← only TX for now
        k = (sig["call"], sig["band"])
        if k not in seen or sig["db"] > seen[k]["db"]:
            seen[k] = sig

    combined = sorted(seen.values(), key=lambda x: x["db"], reverse=True)
    status = "ONLINE" if combined else "DEGRADED"
    print(f"PSKReporter parsed: TX={len(tx)} merged={len(combined)}")
    return {"status": status, "dx_tracks": combined}


# ─── NOAA SWPC ───────────────────────────────────────────────────────
def fetch_space_weather():
    result = {"sfi": "N/A", "kp": "N/A", "geomag": "N/A", "flare_risk": "N/A"}

    try:
        req = urllib.request.Request(
            "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
            headers=HEADERS,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            kp_data = json.loads(resp.read())
        if kp_data:
            latest = kp_data[-1]
            # SWPC product is an ARRAY-of-arrays: [time, kp, ...]
            kp_val = latest[1] if isinstance(latest, list) and len(latest) > 1 else "N/A"
            result["kp"] = sanitize(str(kp_val))
            try:
                result["geomag"] = "STABLE" if float(kp_val) < 4 else "ELEVATED"
            except (ValueError, TypeError):
                result["geomag"] = "N/A"
    except Exception as e:
        print(f"SWPC Kp failed: {e}", file=sys.stderr)

    try:
        req = urllib.request.Request(
            "https://services.swpc.noaa.gov/json/f107_cm_flux.json",
            headers=HEADERS,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            flux = json.loads(resp.read())
        if flux:
            latest = flux[-1]
            val = latest.get("flux", latest.get("adjusted_flux", "N/A"))
            result["sfi"] = sanitize(str(val))
    except Exception as e:
        print(f"SFI fetch failed: {e}", file=sys.stderr)

    return result


# ─── MAIN ────────────────────────────────────────────────────────────
def main():
    print("Initializing BETA 5 Multi-Mission Telemetry Array...")
    solar = fetch_space_weather()
    psk = fetch_psk_telemetry()

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
            "dx_tracks": FICTIONAL_STATIONS + psk["dx_tracks"],
        },
    }

    os.makedirs("data", exist_ok=True)
    with open("data/telemetry.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Written: {len(psk['dx_tracks'])} live signals, status={psk['status']}")


if __name__ == "__main__":
    main()
