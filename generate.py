import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import requests
from PIL import Image, ImageDraw, ImageFont
from icalendar import Calendar
import recurring_ical_events

# --- Konfiguration & Umgebungsvariablen ---
TIMEZONE_STR = os.getenv("TIMEZONE", "Europe/Berlin")
TZ = ZoneInfo(TIMEZONE_STR)
LAT = os.getenv("LATITUDE", "48.96")
LON = os.getenv("LONGITUDE", "9.13")
LOCATION_NAME = os.getenv("LOCATION_NAME", "Bietigheim-Bissingen")
ICAL_URL = os.getenv("ICAL_URL", "")

WIDTH, HEIGHT = 758, 1024
BG_COLOR = 255    # Weiß
TEXT_COLOR = 0    # Schwarz
LINE_COLOR = 180  # Grau

# Deutsche Wochentage & Monate
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
          "Juli", "August", "September", "Oktober", "November", "Dezember"]

WMO_CODES = {
    0: "Klar / Sonnig", 1: "Heiter", 2: "Teilw. bewölkt", 3: "Bedeckt",
    45: "Nebel", 48: "Raureifnebel", 51: "Leichter Niesel", 53: "Nieselregen",
    55: "Starker Niesel", 61: "Leichter Regen", 63: "Regen", 65: "Starker Regen",
    71: "Leichter Schnee", 73: "Schneefall", 75: "Starker Schnee",
    80: "Regenschauer", 81: "Mäßige Schauer", 82: "Heftige Schauer",
    95: "Gewitter"
}

def load_fonts():
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        font_large = ImageFont.truetype(font_bold_path, 32)
        font_medium = ImageFont.truetype(font_bold_path, 20)
        font_regular = ImageFont.truetype(font_path, 17)
        font_small = ImageFont.truetype(font_path, 13)
    except IOError:
        font_large = font_medium = font_regular = font_small = ImageFont.load_default()
    return font_large, font_medium, font_regular, font_small

def draw_weather_icon(draw, x, y, code):
    """Zeichnet scharfe, monochrome Wettersymbole (ca. 36x36 Pixel)"""
    # 1. Sonne / Klar (0, 1)
    if code in (0, 1):
        draw.ellipse([(x + 10, y + 10), (x + 26, y + 26)], fill=255, outline=0, width=2)
        draw.line([(x + 18, y + 3), (x + 18, y + 7)], fill=0, width=2)
        draw.line([(x + 18, y + 29), (x + 18, y + 33)], fill=0, width=2)
        draw.line([(x + 5, y + 18), (x + 9, y + 18)], fill=0, width=2)
        draw.line([(x + 27, y + 18), (x + 31, y + 18)], fill=0, width=2)
        draw.line([(x + 9, y + 9), (x + 12, y + 12)], fill=0, width=2)
        draw.line([(x + 24, y + 9), (x + 27, y + 12)], fill=0, width=2)
        draw.line([(x + 9, y + 27), (x + 12, y + 24)], fill=0, width=2)
        draw.line([(x + 24, y + 27), (x + 27, y + 24)], fill=0, width=2)

    # 2. Teilweise bewölkt (2)
    elif code == 2:
        draw.ellipse([(x + 20, y + 6), (x + 32, y + 18)], fill=255, outline=0, width=2)
        draw.line([(x + 26, y + 2), (x + 26, y + 4)], fill=0, width=2)
        draw.line([(x + 34, y + 12), (x + 36, y + 12)], fill=0, width=2)
        draw.ellipse([(x + 4, y + 16), (x + 18, y + 30)], fill=255, outline=0, width=2)
        draw.ellipse([(x + 12, y + 10), (x + 26, y + 26)], fill=255, outline=0, width=2)
        draw.ellipse([(x + 18, y + 16), (x + 32, y + 30)], fill=255, outline=0, width=2)
        draw.rectangle([(x + 11, y + 20), (x + 25, y + 30)], fill=255)
        draw.line([(x + 10, y + 30), (x + 26, y + 30)], fill=0, width=2)

    # 3. Regen / Schauer (51-65, 80-82)
    elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        draw.ellipse([(x + 4, y + 6), (x + 18, y + 20)], fill=255, outline=0, width=2)
        draw.ellipse([(x + 12, y + 2), (x + 26, y + 16)], fill=255, outline=0, width=2)
        draw.ellipse([(x + 20, y + 6), (x + 34, y + 20)], fill=255, outline=0, width=2)
        draw.rectangle([(x + 11, y + 10), (x + 27, y + 20)], fill=255)
        draw.line([(x + 10, y + 20), (x + 28, y + 20)], fill=0, width=2)
        draw.line([(x + 10, y + 24), (x + 8, y + 31)], fill=0, width=2)
        draw.line([(x + 19, y + 24), (x + 17, y + 31)], fill=0, width=2)
        draw.line([(x + 28, y + 24), (x + 26, y + 31)], fill=0, width=2)

    # 4. Gewitter (95)
    elif code == 95:
        draw.ellipse([(x + 4, y + 4), (x + 18, y + 18)], fill=255, outline=0, width=2)
        draw.ellipse([(x + 12, y + 1), (x + 26, y + 15)], fill=255, outline=0, width=2)
        draw.ellipse([(x + 20, y + 4), (x + 34, y + 18)], fill=255, outline=0, width=2)
        draw.rectangle([(x + 11, y + 8), (x + 27, y + 18)], fill=255)
        draw.line([(x + 10, y + 18), (x + 28, y + 18)], fill=0, width=2)
        draw.polygon([(x + 20, y + 18), (x + 14, y + 26), (x + 19, y + 26), 
                      (x + 15, y + 35), (x + 24, y + 24), (x + 19, y + 24)], fill=0)

    # 5. Schnee (71, 73, 75)
    elif code in (71, 73, 75):
        draw.ellipse([(x + 4, y + 6), (x + 18, y + 20)], fill=255, outline=0, width=2)
        draw.ellipse([(x + 12, y + 2), (x + 26, y + 16)], fill=255, outline=0, width=2)
        draw.ellipse([(x + 20, y + 6), (x + 34, y + 20)], fill=255, outline=0, width=2)
        draw.rectangle([(x + 11, y + 10), (x + 27, y + 20)], fill=255)
        draw.line([(x + 10, y + 20), (x + 28, y + 20)], fill=0, width=2)
        for sx, sy in [(x + 11, y + 26), (x + 25, y + 26)]:
            draw.line([(sx - 3, sy), (sx + 3, sy)], fill=0, width=1)
            draw.line([(sx, sy - 3), (sx, sy + 3)], fill=0, width=1)

    # 6. Nebel (45, 48)
    elif code in (45, 48):
        draw.line([(x + 6, y + 11), (x + 30, y + 11)], fill=0, width=2)
        draw.line([(x + 3, y + 18), (x + 33, y + 18)], fill=0, width=2)
        draw.line([(x + 8, y + 25), (x + 28, y + 25)], fill=0, width=2)

    # 7. Bedeckt / Standard Wolke (3)
    else:
        draw.ellipse([(x + 4, y + 14), (x + 18, y + 28)], fill=255, outline=0, width=2)
        draw.ellipse([(x + 12, y + 8), (x + 26, y + 24)], fill=255, outline=0, width=2)
        draw.ellipse([(x + 18, y + 14), (x + 32, y + 28)], fill=255, outline=0, width=2)
        draw.rectangle([(x + 11, y + 18), (x + 25, y + 28)], fill=255)
        draw.line([(x + 10, y + 28), (x + 26, y + 28)], fill=0, width=2)

def fetch_weather():
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m,precipitation_probability,weather_code"
        f"&timezone={TIMEZONE_STR}&forecast_days=1"
    )
    res = requests.get(url, timeout=10).json()
    hourly = res.get("hourly", {})
    times = hourly.get("time", [])
    
    slots = {"Morgens": "08:00", "Mittags": "13:00", "Abends": "19:00"}
    weather_data = {}
    
    for label, target_time in slots.items():
        match_idx = next((i for i, t in enumerate(times) if t.endswith(target_time)), None)
        if match_idx is not None:
            temp = round(hourly["temperature_2m"][match_idx])
