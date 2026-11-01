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
f_quote = ImageFont.truetype(font_p, 20)
f_quote_author = ImageFont.truetype(font_p, 16)

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
        draw.ellipse([(x+12, y+12), (x+28, y+28)], fill=255, outline=0, width=2)
    elif code == 2:
        draw.ellipse([(x+20, y+4), (x+34, y+18)], fill=255, outline=0, width=2)
        cloud(x, y+6)
    elif code in (45, 48):
        for dy in (12, 20, 28):
            draw.line([(x+6, y+dy), (x+36, y+dy)], fill=0, width=2)
    else:
        cloud(x, y)
        if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
            for rx in (13, 21, 29):
                draw.line([(x+rx, y+30), (x+rx-3, y+38)], fill=0, width=2)
        elif code in (71, 73, 75, 77, 85, 86):
            for sx in (13, 21, 29):
                draw.line([(x+sx-3, y+34), (x+sx+3, y+34)], fill=0, width=2)
                draw.line([(x+sx, y+31), (x+sx, y+37)], fill=0, width=2)
        elif code in (95, 96, 99):
            draw.polygon([(x+22, y+27), (x+15, y+35), (x+20, y+35), (x+17, y+42), (x+27, y+32), (x+21, y+32)], fill=0)

def get_events(cal, target_date):
    if not cal:
        return []
    start_dt = datetime.combine(target_date, time.min).replace(tzinfo=TZ)
    end_dt = datetime.combine(target_date, time.max).replace(tzinfo=TZ)
    parsed = []
    for ev in recurring_ical_events.of(cal).between(start_dt, end_dt):
        summary = str(ev.get("SUMMARY", "Ohne Titel")).strip()
        dtstart = ev.get("DTSTART").dt
        dtend = ev.get("DTEND").dt if ev.get("DTEND") else None
        if not isinstance(dtstart, datetime):
            parsed.append((-1, "Ganztägig", summary))
        else:
            s_loc = dtstart.astimezone(TZ)
            if isinstance(dtend, datetime):
                t_str = f"{s_loc.strftime('%H:%M')} - {dtend.astimezone(TZ).strftime('%H:%M')}"
            else:
                t_str = f"{s_loc.strftime('%H:%M')} Uhr"
            parsed.append((s_loc.hour * 60 + s_loc.minute, t_str, summary))
    return sorted(parsed, key=lambda x: (x[0], x[2]))

def get_daily_quote():
    try:
        r = requests.get("https://api.zitat-service.de/v1/quote?language=de", timeout=10)
        data = r.json()
        quote = data.get("quote", "").strip()
        author = data.get("authorName", "").strip()
        if quote:
            return quote, author
    except Exception:
        pass
    return "Der beste Weg, die Zukunft vorherzusagen, ist, sie zu gestalten.", "Peter Drucker"

def wrap_text(draw_obj, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + (" " if current else "") + word
        if draw_obj.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

# --- Bild erstellen ---
now = datetime.now(TZ)
img = Image.new("L", (WIDTH, HEIGHT), 255)
draw = ImageDraw.Draw(img)

# Schwarzer Balken oben (verdeckt den Bereich der Kindle-Statusleiste)
BAR_HEIGHT = 42
draw.rectangle([(0, 0), (WIDTH, BAR_HEIGHT)], fill=0)

GAP = 10
TOP = BAR_HEIGHT + GAP

# 1. Header
date_str = f"{WOCHENTAGE[now.weekday()]}, {now.day}. {MONATE[now.month - 1]} {now.year}"
draw.text((30, TOP), date_str, fill=0, font=f_large)
draw.line([(30, TOP + 38 + GAP), (WIDTH - 30, TOP + 38 + GAP)], fill=180, width=2)

# 2. Wetter
print("2/4 Lade Wetterdaten...")
weather_start = TOP + 38 + GAP + 14
draw.text((30, weather_start), f"WETTER HEUTE – {LOCATION_NAME.upper()}", fill=0, font=f_medium)
upd_str = f"Stand: {now.strftime('%H:%M')} Uhr"
draw.text((WIDTH - 30 - draw.textlength(upd_str, font=f_small), weather_start + 5), upd_str, fill=90, font=f_small)

url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,precipitation_probability,weather_code&timezone={TIMEZONE_STR}&forecast_days=1"
try:
    hourly = requests.get(url, timeout=12).json().get("hourly", {})
    times = hourly.get("time", [])
except Exception:
    hourly = {}
    times = []

for i, (label, t_target) in enumerate([("Morgens (08:00)", "08:00"), ("Mittags (13:00)", "13:00"), ("Abends (19:00)", "19:00")]):
    x = 30 + i * ((WIDTH - 60) // 3)
    idx = next((k for k, t in enumerate(times) if t.endswith(t_target)), 0)
    code = hourly.get("weather_code", [3])[idx] if times else 3
    temp = f"{round(hourly.get('temperature_2m', [0])[idx])}°C" if times else "–"
    rain = f"{hourly.get('precipitation_probability', [0])[idx]}% Regen" if times else ""
    draw.text((x, weather_start + 38), label, fill=90, font=f_small)
    draw_icon(draw, x, weather_start + 62, code)
    draw.text((x + 48, weather_start + 64), temp, fill=0, font=f_temp)
    draw.text((x, weather_start + 110), WMO_CODES.get(code, "Bedeckt"), fill=0, font=f_regular)
    draw.text((x, weather_start + 134), rain, fill=90, font=f_small)

draw.line([(30, weather_start + 167), (WIDTH - 30, weather_start + 167)], fill=180, width=2)

# 3. Kalender
print("3/4 Lade Kalenderdaten...")
cal = None
if ICAL_URL:
    try:
        cal = Calendar.from_ical(requests.get(ICAL_URL, timeout=15).text)
    except Exception:
        cal = None

tomorrow = now.date() + timedelta(days=1)
sections = [
    ("TERMINE HEUTE", get_events(cal, now.date())),
    (f"TERMINE MORGEN ({WOCHENTAGE[tomorrow.weekday()]}, {tomorrow.day}.{tomorrow.month:02d}.)", get_events(cal, tomorrow))
]

y = weather_start + 187
for s_idx, (title, ev_list) in enumerate(sections):
    draw.text((30, y), title, fill=0, font=f_medium)
    y += 36
    if not ev_list:
        draw.text((30, y), "Keine Termine eingetragen.", fill=90, font=f_regular)
        y += 36
    for _, t_str, summary in ev_list[:6]:
        if y > HEIGHT - 160:
            break
        draw.text((30, y), t_str, fill=0, font=f_regular)
        while len(summary) > 3 and draw.textlength(summary, font=f_regular) > (WIDTH - 225):
            summary = summary[:-2] + "…"
        draw.text((195, y), summary, fill=0, font=f_regular)
        y += 36
        draw.line([(30, y - 7), (WIDTH - 30, y - 7)], fill=230, width=1)
    if s_idx == 0:
        y += 12
        draw.line([(30, y), (WIDTH - 30, y)], fill=180, width=2)
        y += 20

# 4. Zitat unten
print("4/4 Lade Zitat und speichere Bild...")
quote, author = get_daily_quote()
quote_lines = wrap_text(draw, f"„{quote}“", f_quote, WIDTH - 80)
quote_y = HEIGHT - 130
draw.line([(30, quote_y - 15), (WIDTH - 30, quote_y - 15)], fill=180, width=1)
for line in quote_lines[:3]:
    draw.text((40, quote_y), line, fill=0, font=f_quote)
    quote_y += 26
if author:
    draw.text((40, quote_y + 4), f"— {author}", fill=80, font=f_quote_author)

img.save("dashboard.png", "PNG")
print("Fertig: dashboard.png erfolgreich gespeichert!")
