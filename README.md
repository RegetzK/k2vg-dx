# K2VG DX Monitor — BETA 5 Interstellar Monitoring Station Panel

Deep cover IC-7300 & BETA 5 Transceiver Array.
Live PSKReporter + NOAA SWPC telemetry for FM05 (Raleigh/Cary, NC)

## Endpoints

| Target | URL |
|--------|-----|
| QRZ iframe | https://regetzk.github.io/k2vg-dx/ |
| Desktop console | https://regetzk.github.io/k2vg-dx/docs/desktop.html |
| Raw telemetry JSON | https://regetzk.github.io/k2vg-dx/data/telemetry.json |

## Architecture

- **GitHub Actions** (5-min cron) runs `proxy/fetch_telemetry.py`
- Fetches PSKReporter XML + NOAA SWPC JSON directly (no third-party proxies)
- Writes `data/telemetry.json` → commits → GitHub Pages serves it
- Widgets fetch the JSON client-side (no server, no API keys, no secrets)

## ZT Compliance

- No secrets in repo
- No third-party CORS proxies
- No outbound notifications
- Public APIs only (PSKReporter, NOAA SWPC)
- Actions runner is ephemeral

## SNR Filter

- Range: -15 to -24 dB
- Accounts for Decodium 4.0 Shannon multi-cycle integration gain (~3-5 dB)
  vs single-pass decoders reporting to PSKReporter

## Maintenance

- Manual trigger: Actions tab → "BETA 5 Telemetry Update" → "Run workflow"
- Change poll interval: edit `cron` in `.github/workflows/widget.yml` (min 5 min on free tier)
- Update QSO counts: edit `QSO_TOTAL` / `QSO_CONFIRMED_QRZ` in `proxy/fetch_telemetry.py`   
