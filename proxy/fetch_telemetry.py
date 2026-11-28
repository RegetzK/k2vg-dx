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
LAST_SECONDS = 7200        # 2 hour window

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

def fetch_rx():
    """Query PSKReporter for spots where K2VG is the receiver (RX view)."""
    url = (
        f"https://retrieve.pskreporter.info/query"
        f"?receiverCallsign={STATION_CALL}"
        f"&flowStartSeconds=-{LAST_SECONDS}"
        f"&rronly=1&rptlimit=200&mode=FT8"
    )
    print(f"RX Query: {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    print(f"RX: Received {len(data)} bytes")
    return data

def fetch_tx():
    """Query PSKReporter for spots where K2VG is the sender (TX view)."""
    url = (
        f"https://retrieve.pskreporter.info/query"
        f"?senderCallsign={STATION_CALL}"
        f"&flowStartSeconds=-{LAST_SECONDS}"
        f"&rronly=1&rptlimit=200&mode=FT8"
    )
    print(f"TX Query: {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    print(f"TX: Received {len(data)} bytes")
    return data

# ─── PARSE ────────────────────────────────────────────────────────────

def _safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def parse_spots(xml_bytes, direction):
    """Parse <receptionReport> elements into track dicts.
    direction: 'rx' if K2VG is receiver, 'tx' if K2VG is sender.
    """
    root = ET.fromstring(xml_bytes)
    tracks = []
    seen = set()
    for rpt in root.iter("receptionReport"):
        # Direction-aware field selection
        if direction == "rx":
            call = rpt.get("senderCallsign", "")
            grid = rpt.get("senderLocator", "") or "????"
            dxcc = rpt.get("senderDXCC", "")
            dxcc_code = rpt.get("senderDXCCCode", "")
        else:
            call = rpt.get("receiverCallsign", "")
            grid = rpt.get("receiverLocator", "") or "????"
            dxcc = rpt.get("receiverDXCC", "")
            dxcc_code = rpt.get("receiverDXCCCode", "")

        if not call or call in seen:
            continue
        seen.add(call)

        freq_hz = _safe_int(rpt.get("frequency", "0"))
        db = _safe_int(rpt.get("sNR", "0"))
        ts_ms = _safe_int(rpt.get("flowStartSeconds", "0")) * 1000

        tracks.append({
            "call": call,
            "grid": grid[:4],
            "band": None,
            "freq": freq_hz / 1e6,
            "db": db,
            "dxcc": dxcc or dxcc_code,
            "dxcc_code": dxcc_code,
            "timestamp": ts_ms,
            "direction": direction,
            "status": "SPOTTED",
            "lore": False,
        })
    print(f"Parsed {len(tracks)} unique spots ({direction.upper()})")
    return tracks

# ─── MAIN ─────────────────────────────────────────────────────────────

def main():
    status = "ONLINE"
    tracks = []
    errors = []

    try:
        rx_bytes = fetch_rx()
        tracks.extend(parse_spots(rx_bytes, "rx"))
    except Exception as e:
        print(f"RX FETCH ERROR: {e}", file=sys.stderr)
        errors.append("RX")

    try:
        tx_bytes = fetch_tx()
        tracks.extend(parse_spots(tx_bytes, "tx"))
    except Exception as e:
        print(f"TX FETCH ERROR: {e}", file=sys.stderr)
        errors.append("TX")

    if errors:
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

    with open("data/telemetry.js", "w") as f:
        f.write("window.TELEMETRY_DATA = ")
        f.write(json.dumps(output))
        f.write(";")

    print(f"Done: {len(tracks)} real tracks, status={status}, errors={errors or 'none'}")

    if status == "DEGRADED":
        sys.exit(1)

if __name__ == "__main__":
    main()   
