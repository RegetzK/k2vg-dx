#!/usr/bin/env python3
"""
BETA 5 Multi-Mission Telemetry Array
Direct API fetch — no third-party proxies. ZT compliant.
Uses retrieve.pskreporter.info/query per PSKReporter dev docs.
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ─── CONFIG ───────────────────────────────────────────────────────────
STATION_CALL = "K2VG"
MY_GRID = "FM18"           # internal only — never written to output
PUBLIC_GRID = "FM05"       # OPSEC — what goes in JSON / QRZ
QSO_TOTAL = 124
QSO_CONFIRMED_QRZ = 100
SNR_MIN = -24
SNR_MAX = 24
LAST_SECONDS = 3600        # 1 hour window

FICTIONAL_STATIONS = [
    {"call": "NCC-1701", "grid": "GSO-FM05", "band": "ALL", "db": None, "freq": None, "dxcc": "USS ENTERPRISE", "status": "UPLINK ACTIVE", "lore": True},
    {"call": "N/A", "grid": "40 ERIDANI A", "band": "ALL", "db": None, "freq": None, "dxcc": "VULCAN", "status": "MONITORING 🖖", "lore": True},
    {"call": "IC/MIL/GOV COMMS", "grid": "ALL", "band": "ALL", "db": None, "freq": None, "dxcc": "EARTH", "status": "MONITORED", "lore": True},
    {"call": "CIV WEB/DARK WEB/COMMS", "grid": "ALL", "band": "ALL", "db": None, "freq": None, "dxcc": "EARTH", "status": "MONITORED", "lore": True},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; K2VG-BETA5-Telemetry/1.0; ham-radio telemetry)",
    "Accept": "application/xml, text/xml, */*",
}

# ─── FETCH ────────────────────────────────────────────────────────────

def fetch_spots():
    """Query PSKReporter for spots where K2VG is the receiver (RX view)."""
    url = (
        f"https://retrieve.pskreporter.info/query"
        f"?receiverCallsign={STATION_CALL}"
        f"&flowStartSeconds=-{LAST_SECONDS}"
        f"&rronly=1"
        f"&rptlimit=200"
    )
    print(f"Query: {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    print(f"Received {len(data)} bytes")
    return data

def parse_spots(xml_bytes):
    """Parse <receptionReport> elements into track dicts."""
    root = ET.fromstring(xml_bytes)
    tracks = []
    seen = set()
    for rpt in root.iter("receptionReport"):
        call = rpt.get("senderCallsign", "")
        if not call or call in seen:
            continue
        seen.add(call)
        freq_str = rpt.get("frequency", "0")
        try:
            freq_hz = int(freq_str)
        except (ValueError, TypeError):
            freq_hz = 0
        grid = rpt.get("senderLocator", "") or "????"
        dxcc_code = rpt.get("senderDXCCcode", "") or call[:2]
        tracks.append({
            "call": call,
            "grid": grid,
            "band": None,
            "freq": freq_hz,
            "db": None,
            "dxcc": dxcc_code,
            "lore": False,
        })
    print(f"Parsed {len(tracks)} unique senders")
    return tracks

# ─── MAIN ─────────────────────────────────────────────────────────────

def main():
    status = "ONLINE"
    tracks = []

    try:
        xml_bytes = fetch_spots()
        tracks = parse_spots(xml_bytes)
    except Exception as e:
        print(f"FETCH ERROR: {e}", file=sys.stderr)
        status = "DEGRADED"

    output = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "station": {
            "callsign": STATION_CALL,
            "grid": PUBLIC_GRID,
            "total_qsos": QSO_TOTAL,
            "confirmed_qrz": QSO_CONFIRMED_QRZ,
        },
        "solar": {
            "sfi": "N/A",
            "kp": "N/A",
            "geomag": "STABLE",
            "flare_risk": "N/A",
        },
        "telemetry": {
            "status": status,
            "dx_tracks": FICTIONAL_STATIONS + tracks,
        },
    }

    os.makedirs("data", exist_ok=True)
    with open("data/telemetry.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Done: {len(tracks)} real tracks, status={status}")

    if status == "DEGRADED":
        sys.exit(1)

if __name__ == "__main__":
    main()   
