import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# --- SYSTEM COORDINATES & ZERO-TRUST CONFIGURATION MATRIX ---
MY_GRID = "FM18"
STATION_CALL = "K2VG"

# Core Station Metadata Totals (Manual override fields for free-tier logs)
QSO_TOTAL = 124
QSO_CONFIRMED_QRZ = 100

# Strict Decodium 4.0 target prefix filtering array (Asia, Oceania, Africa)
TARGET_PREFIXES = (
    "ZL", "ZS", "V5", "3B", "A2", "7Q", "9J", "A9", "9M", "JA", 
    "UA9", "BY", "DU", "YB", "VK", "5H", "5X", "9X", "D2", "EL"
)

# --- FICTIONAL LORE VARIABLES (ASSIGNMENT: EARTH / DECODIUM TARGET MATRIX) ---
FICTIONAL_STATIONS = [
    {"call": "NCC-1701", "grid": "ST01", "db": -16, "freq": 144.1701, "time": "LIVE"},
    {"call": "VULCAN-1", "grid": "40ER", "db": -18, "freq": 50.4010, "time": "LIVE"},
    {"call": "CIV-MON-03", "grid": "DC68", "db": -15, "freq": 7.0680, "time": "LIVE"},
    {"call": "GOV-SAT-09", "grid": "FL68", "db": -19, "freq": 10.1450, "time": "LIVE"}
]
