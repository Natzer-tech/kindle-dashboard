import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import requests
from PIL import Image, ImageDraw, ImageFont
from icalendar import Calendar
import recurring_ical_events

print("1/4 Starte Dashboard-Generierung...")

TIMEZONE_STR = os.getenv("TIMEZONE", "Europe/Berlin")
TZ = ZoneInfo(TIMEZONE_STR)
LAT = os.getenv("LATITUDE", "48.96")
LON = os.getenv("LONGITUDE", "9.13")
LOCATION_NAME = os.getenv("LOCATION_NAME", "Bietigheim-Bissingen")
ICAL_URL = os.getenv("ICAL_URL", "").strip().replace("webcal://", "https://")

WIDTH, HEIGHT = 758, 1024
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]

WMO_CODES = {
    0: "Klar / Sonnig", 1: "Überw. sonnig", 2: "Teilw. bewölkt", 3: "Bedeckt",
    45: "Nebel", 48: "Raureifnebel", 51: "Leichter Niesel", 53: "Nieselregen",
    55: "Starker Niesel", 56: "Gefrier. Niesel", 57: "Starker gefr. Niesel",
    61: "Leichter Regen", 63: "Regen", 65: "Starker Regen", 66: "Gefrier. Regen",
    67: "Starker gefr. Regen", 71: "Leichter Schnee", 73: "Schneefall", 75: "Starker Schnee",
    77: "Schneegriesel", 80: "Leichte Schauer", 81: "Regenschauer", 82: "Heftige Schauer",
    85: "Schneeschauer", 86: "Starke Schneeschauer", 95: "Gewitter", 96: "Gewitter m. Hagel", 99: "Starkes Gewitter"
}

font_p = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_b = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f_large = ImageFont.truetype(font_b, 30)
f_temp = ImageFont.truetype(font_b, 34)
f_medium = ImageFont.truetype(font_b, 20)
f_regular = ImageFont.truetype(font_p, 18)
f_small = ImageFont.truetype(font_p, 14)
f_quote = ImageFont.truetype(font_p, 18)
f_quote_author = ImageFont.truetype(font_p, 15)

def draw_icon(draw, x, y, code):
    def cloud(cx, cy):
        for dx, dy, r in [(12, 18, 8), (21, 13, 10), (30, 18, 8)]:
            draw.ellipse([(cx+dx-r, cy+dy-r), (cx+dx+r, cy+dy+r)], fill=255, outline=0, width=2)
        draw.rectangle([(cx+12, cy+16), (cx+30, cy+26)], fill=255)
        draw.line([(cx+10, cy+26), (cx+32, cy+26)], fill=0, width=2)

    if code in (0, 1):
        for dx, dy in [(15, 0), (0, 15), (11, 11), (-11, 11)]:
            draw.line([(x+20-dx, y+20-dy), (x+20+dx, y+20+dy)], fill=0, width=2)
        draw.ellipse([(x+9, y+9), (x+31, y+31)], fill=255)
        draw.ellipse([(x+12, y+12), (x+28, y+28)], 
