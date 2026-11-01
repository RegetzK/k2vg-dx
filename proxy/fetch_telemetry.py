# ─── FETCH ────────────────────────────────────────────────────────────
PUBLIC_GRID = "FM05"  # OPSEC — never expose MY_GRID

def fetch_spots():
    """Query PSKReporter for spots where K2VG is the receiver (RX view)."""
    url = (
        f"https://retrieve.pskreporter.info/query"
        f"?receiverCallsign={STATION_CALL}"
        f"&flowStartSeconds=-{LAST_SECONDS}"
        f"&rronly=1"
        f"&rptlimit=200"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()

def parse_spots(xml_bytes):
    """Parse receptionReport elements into track dicts."""
    root = ET.fromstring(xml_bytes)
    tracks = []
    seen = set()
    for rpt in root.iter("receptionReport"):
        call = rpt.get("senderCallsign", "")
        if not call or call in seen:
            continue
        seen.add(call)
        freq_hz = rpt.get("frequency", "0")
        freq_hz = int(freq_hz) if freq_hz else 0
        grid = rpt.get("senderLocator", "")
        dxcc = rpt.get("senderDXCCcode", "")
        # PSKReporter doesn't expose SNR in the HTTP API — leave null
        tracks.append({
            "call": call,
            "grid": grid or "????",
            "band": None,          # front-end derives from freq
            "freq": freq_hz,       # Hz — front-end divides by 1e6
            "db": None,            # not available via HTTP API
            "dxcc": dxcc or call[:2],
            "lore": False,
        })
    return tracks

# ─── MAIN ─────────────────────────────────────────────────────────────
def main():
    status = "ONLINE"
    try:
        xml_bytes = fetch_spots()
        tracks = parse_spots(xml_bytes)
    except Exception as e:
        print(f"FETCH ERROR: {e}", file=sys.stderr)
        status = "DEGRADED"
        tracks = []

    # Build output
    output = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "station": {
            "callsign": STATION_CALL,
            "grid": PUBLIC_GRID,       # ← OPSEC: FM05, never MY_GRID
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
    print(f"Wrote {len(tracks)} real tracks, status={status}")

if __name__ == "__main__":
    main()   
