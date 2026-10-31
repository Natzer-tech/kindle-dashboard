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

# Deutsche Wochentage & Monate (verhindert englische Ausgabe auf Ubuntu-Servern)
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
        draw.line([(x + 24, y + 9), (x + 27, y + 12
