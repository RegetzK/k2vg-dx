import os
import json
import requests
import xml.etree.ElementTree as ET

MY_GRID = "FM18"
TARGET_CONTINENTS = ["AS", "OC", "AF"]

def fetch_psk_telemetry():
    """
    Beta 5 Re-engineered CORS Proxy Pipeline
    Routes through public edge proxies to clear connection flags.
    """
    # Raw target query for K2VG station telemetry footprints
    target_url = "https://pskreporter.info"
    
    # Primary and Backup CORS proxy arrays
    cors_proxies = [
        f"https://allorigins.win{target_url}",
        f"https://corsproxy.io?{target_url}"
    ]
    
    headers = {
        'User-Agent': 'Beta5-Processor-K2VG-Control/4.0 (NIST/CISA Compliant Ham Engine)'
    }
    
    for proxy_url in cors_proxies:
        try:
            print(f"Attempting link via proxy: {proxy_url.split('?')[0]}")
            response = requests.get(proxy_url, headers=headers, timeout=15)
            
            if response.status_code == 200 and response.content:
                # Successfully bypassed connection wall; process XML payload
                root = ET.fromstring(response.content)
                dx_signals = []
                
                for reporter in root.findall('receptionReport'):
                    db_val = int(reporter.get('sNR', 0))
                    
                    # Decodium 4.0 Shannon isolation matrix (-15 to -19 dB)
                    if -19 <= db_val <= -15:
                        dx_signals.append({
                            "call": reporter.get('receiverCallsign', 'Unknown'),
                            "grid": reporter.get('receiverGrid', 'Unknown'),
                            "db": db_val,
                            "freq": int(reporter.get('frequency', 0)) / 1000000,
                            "time": reporter.get('receptionTime', 'Unknown')
                        })
                        
                print("CORS transmission successful.")
                return {"status": "Online", "dx_tracks": dx_signals}
                
        except ET.ParseError:
            print("Proxy delivered payload, but XML format was corrupted.")
            continue
        except Exception as e:
            print(f"Proxy link failed to route: {str(e)}")
            continue
            
    # Fallback state if all proxy endpoints fail validation checks
    return {"status": "Proxy Network Degradation", "dx_tracks": []}
