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
ICAL_URL = os.getenv("ICAL_URL", "").strip()

# Automatischer Fix, falls webcal:// statt https:// hinterlegt wurde
if ICAL_URL.startswith("webcal://"):
    ICAL_URL = "https://" + ICAL_URL[len("webcal://"):]

WIDTH, HEIGHT = 758, 1024
BG_COLOR = 255    # Weiß
TEXT_COLOR = 0    # Schwarz
GRAY_DARK = 90    # Dunkelgrau für Zusatzinfos
LINE_COLOR = 180  # Mittelgrau für Trennlinien

WOCHENTAGE = [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag",
    "Freitag", "Samstag", "Sonntag"
]
MONATE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]

# Vollständige WMO-Wettercodes von Open-Meteo
WMO_CODES = {
    0: "Klar / Sonnig",
    1: "Überw. sonnig",
    2: "Teilw. bewölkt",
    3: "Bedeckt",
    45: "Nebel",
    48: "Raureifnebel",
    51: "Leichter Niesel",
    53: "Nieselregen",
    55: "Starker Niesel",
    56: "Gefrier. Niesel",
    57: "Starker gefr. Niesel",
    61: "Leichter Regen",
    63: "Regen",
    65: "Starker Regen",
    66: "Gefrier. Regen",
    67: "Starker gefr. Regen",
    71: "Leichter Schnee",
    73: "Schneefall",
    75: "Starker Schnee",
    77: "Schneegriesel",
    80: "Leichte Schauer",
    81: "Regenschauer",
    82: "Heftige Schauer",
    85: "Schneeschauer",
    86: "Starke Schneeschauer",
    95: "Gewitter",
    96: "Gewitter m. Hagel",
    99: "Starkes Gewitter"
}


def load_fonts():
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        font_large = ImageFont.truetype(font_bold_path, 30)
        font_temp = ImageFont.truetype(font_bold_path, 34)
        font_medium = ImageFont.truetype(font_bold_path, 20)
        font_regular = ImageFont.truetype(font_path, 18)
        font_small = ImageFont.truetype(font_path, 14)
    except IOError:
        default = ImageFont.load_default()
        return default, default, default, default, default
    return font_large, font_temp, font_medium, font_regular, font_small


def truncate_text_pixel(draw, text, font, max_width):
    """Kürzt Text exakt anhand der tatsächlichen Pixelbreite."""
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "..."
    while len(text) > 0 and draw.textlength(text + ellipsis, font=font) > max_width:
        text = text[:-1]
    return text.rstrip() + ellipsis


def draw_cloud(draw, x, y):
    """Hilfsfunktion für eine saubere Wolkenform."""
    draw.ellipse([(x + 4, y + 12), (x + 20, y + 28)], fill=255, outline=0, width=2)
    draw.ellipse([(x + 12, y + 5), (x + 30, y + 23)], fill=255, outline=0, width=2)
    draw.ellipse([(x + 22, y + 12), (x + 38, y + 28)], fill=255, outline=0, width=2)
    draw.rectangle([(x + 11, y + 16), (x + 31, y + 28)], fill=255)
    draw.line([(x + 10, y + 28), (x + 32, y + 28)], fill=0, width=2)


def draw_weather_icon(draw, x, y, code):
    """Zeichnet monochrome Wettersymbole (ca. 42x42 Pixel)."""
    # 1. Sonne / Klar (0, 1)
    if code in (0, 1):
        draw.ellipse([(x + 11, y + 11), (x + 29, y + 29)], fill=255, outline=0, width=2)
        draw.line([(x + 20, y + 3), (x + 20, y + 8)], fill=0, width=2)
        draw.line([(x + 20, y + 32), (x + 20, y + 37)], fill=0, width=2)
        draw.line([(x + 3, y + 20), (x + 8, y + 20)], fill=0, width=2)
        draw.line([(x + 32, y + 20), (x + 37, y + 20)], fill=0, width=2)
        draw.line([(x + 8, y + 8), (x + 12, y + 12)], fill=0, width=2)
        draw.line([(x + 28, y + 8), (x + 32, y + 12)], fill=0, width=2)
        draw.line([(x + 8, y + 32), (x + 12, y + 28)], fill=0, width=2)
        draw.line([(x + 28, y + 32), (x + 32, y + 28)], fill=0, width=2)

    # 2. Teilweise bewölkt (2)
    elif code == 2:
        draw.ellipse([(x + 22, y + 4), (x + 36, y + 18)], fill=255, outline=0, width=2)
        draw.line([(x + 29, y + 0), (x + 29, y + 3)], fill=0, width=2)
        draw.line([(x + 38, y + 11), (x + 41, y + 11)], fill=0, width=2)
        draw_cloud(draw, x, y + 6)

    # 3. Regen, Niesel & Schauer (51-67, 80-82)
    elif code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        draw_cloud(draw, x, y)
        draw.line([(x + 12, y + 31), (x + 9, y + 39)], fill=0, width=2)
        draw.line([(x + 21, y + 31), (x + 18, y + 39)], fill=0, width=2)
        draw.line([(x + 30, y + 31), (x + 27, y + 39)], fill=0, width=2)

    # 4. Gewitter (95, 96, 99)
    elif code in (95, 96, 99):
        draw_cloud(draw, x, y)
        pts = [
            (x + 22, y + 28), (x + 15, y + 36), (x + 20, y + 36),
            (x + 17, y + 43), (x + 27, y + 33), (x + 21, y + 33)
        ]
        draw.polygon(pts, fill=0)

    # 5. Schnee (71-77, 85, 86)
    elif code in (71, 73, 75, 77, 85, 86):
        draw_cloud(draw, x, y)
        for sx, sy in [(x + 13, y + 35), (x + 21, y + 37), (x + 29, y + 35)]:
            draw.line([(sx - 3, sy), (sx + 3, sy)], fill=0, width=2)
            draw.line([(sx, sy - 3), (sx, sy + 3)], fill=0, width=2)

    # 6. Nebel (45, 48)
    elif code in (45, 48):
        draw.line([(x + 6, y + 12), (x + 34, y + 12)], fill=0, width=2)
        draw.line([(x + 2, y + 20), (x + 38, y + 20)], fill=0, width=2)
        draw.line([(x + 8, y + 28), (x + 32, y + 28)], fill=0, width=2)

    # 7. Bedeckt / Standard-Wolke (3 und sonstige)
    else:
        draw_cloud(draw, x, y + 5)


def fetch_weather():
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m,precipitation_probability,weather_code"
        f"&timezone={TIMEZONE_STR}&forecast_days=1"
    )
    slots = {"Morgens (08:00)": "08:00", "Mittags (13:00)": "13:00", "Abends (19:00)": "19:00"}
    weather_data = {}

    try:
        res = requests.get(url, timeout=10).json()
        hourly = res.get("hourly", {})
        times = hourly.get("time", [])

        for label, target_time in slots.items():
            match_idx = next((i for i, t in enumerate(times) if t.endswith(target_time)), None)
            if match_idx is not None:
                temp = round(hourly["temperature_2m"][match_idx])
                rain = hourly["precipitation_probability"][match_idx]
                code = hourly["weather_code"][match_idx]
                weather_data[label] = {
                    "temp": f"{temp}°C",
                    "rain": f"{rain}% Regenwahrsch.",
                    "desc": WMO_CODES.get(code, "Bedeckt"),
                    "code": code
                }
            else:
                weather_data[label] = {"temp": "--", "rain": "--", "desc": "--", "code": 3}
    except Exception:
        for label in slots:
            weather_data[label] = {"temp": "--", "rain": "Fehler", "desc": "Kein Netz", "code": 3}

    return weather_data


def load_calendar():
    """Lädt den iCal-Kalender genau einmal herunter."""
    if not ICAL_URL:
        return None, "Kein ICAL_URL Secret hinterlegt"
    try:
        resp = requests.get(ICAL_URL, timeout=15)
        resp.raise_for_status()
        return Calendar.from_ical(resp.text), None
    except Exception as e:
        return None, f"Kalender-Fehler: {str(e)[:30]}"


def get_events_for_day(cal, target_date):
    """Filtert alle Termine für ein bestimmtes Datum aus dem geladenen Kalender."""
    start_dt = datetime.combine(target_date, time.min).replace(tzinfo=TZ)
    end_dt = datetime.combine(target_date, time.max).replace(tzinfo=TZ)

    events = recurring_ical_events.of(cal).between(start_dt, end_dt)
    parsed = []

    for event in events:
        summary = str(event.get("SUMMARY", "Ohne Titel")).strip()
        dtstart = event.get("DTSTART").dt
        dtend = event.get("DTEND").dt if event.get("DTEND") else None

        # Unterscheidung: Ganztägig (date) vs. Uhrzeit-Termin (datetime)
        if not isinstance(dtstart, datetime):
            time_str = "Ganztägig"
            sort_key = -1
        else:
            dtstart_local = dtstart.astimezone(TZ)
            sort_key = dtstart_local.hour * 60 + dtstart_local.minute
            if dtend and isinstance(dtend, datetime):
                dtend_local = dtend.astimezone(TZ)
                time_str = f"{dtstart_local.strftime('%H:%M')} - {dtend_local.strftime('%H:%M')}"
            else:
                time_str = f"{dtstart_local.strftime('%H:%M')} Uhr"

        parsed.append((sort_key, time_str, summary))

    parsed.sort(key=lambda x: (x[0], x[2]))
    return parsed


def draw_event_section(draw, title, events, err_msg, start_y, max_events, fonts):
    """Zeichnet einen Terminblock (Heute oder Morgen) und gibt das neue Y zurück."""
    _, _, f_medium, f_regular, _ = fonts
    y = start_y

    draw.text((30, y), title, fill=TEXT_COLOR, font=f_medium)
    y += 36

    if err_msg:
        draw.text((30, y), err_msg, fill=TEXT_COLOR, font=f_regular)
        return y + 36

    if not events:
        draw.text((30, y), "Keine Termine eingetragen.", fill=GRAY_DARK, font=f_regular)
        return y + 36

    for _, time_str, summary in events[:max_events]:
        if y > HEIGHT - 45:
            break
        draw.text((30, y), time_str, fill=TEXT_COLOR, font=f_regular)
        clean_title = truncate_text_pixel(draw, summary, f_regular, WIDTH - 220)
        draw.text((190, y), clean_title, fill=TEXT_COLOR, font=f_regular)
        y += 36
        draw.line([(30, y - 7), (WIDTH - 30, y - 7)], fill=230, width=1)

    return y


def render_dashboard():
    now = datetime.now(TZ)
    img = Image.new("L", (WIDTH, HEIGHT), BG_COLOR)
