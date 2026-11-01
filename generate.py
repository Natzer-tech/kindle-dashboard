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
    0: "Klar", 1: "Sonnig", 2: "Teilweise bewölkt", 3: "Bedeckt",
    45: "Nebel", 48: "Raureifnebel", 51: "Leichter Niesel", 53: "Niesel",
    55: "Starker Niesel", 56: "Gefrierender Niesel", 57: "Starker gefr. Niesel",
    61: "Leichter Regen", 63: "Regen", 65: "Starker Regen", 66: "Gefrierender Regen",
    67: "Starker gefr. Regen", 71: "Leichter Schnee", 73: "Schnee", 75: "Starker Schnee",
    77: "Schneegriesel", 80: "Leichte Schauer", 81: "Regenschauer", 82: "Heftige Schauer",
    85: "Schneeschauer", 86: "Starke Schneeschauer", 95: "Gewitter", 96: "Gewitter m. Hagel", 99: "Starkes Gewitter"
}

font_p = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_b = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

f_title = ImageFont.truetype(font_b, 32)
f_section = ImageFont.truetype(font_b, 22)
f_temp = ImageFont.truetype(font_b, 38)
f_label = ImageFont.truetype(font_b, 16)
f_regular = ImageFont.truetype(font_p, 18)
f_small = ImageFont.truetype(font_p, 14)
f_tiny = ImageFont.truetype(font_p, 12)

def draw_icon(draw, x, y, code, size=48):
    s = size
    if code in (0, 1):  # Sonne
        draw.ellipse([(x+12, y+12), (x+s-12, y+s-12)], fill=0)
        for ang in range(0, 360, 45):
            import math
            rad = math.radians(ang)
            x1 = x + s/2 + math.cos(rad)*18
            y1 = y + s/2 + math.sin(rad)*18
            x2 = x + s/2 + math.cos(rad)*24
            y2 = y + s/2 + math.sin(rad)*24
            draw.line([(x1, y1), (x2, y2)], fill=0, width=3)
    elif code == 2:  # Teilweise bewölkt
        draw.ellipse([(x+8, y+18), (x+28, y+38)], outline=0, width=2)
        draw.ellipse([(x+20, y+10), (x+40, y+30)], fill=255, outline=0, width=2)
    else:
        # Wolke
        draw.ellipse([(x+8, y+18), (x+22, y+32)], fill=0)
        draw.ellipse([(x+18, y+10), (x+36, y+28)], fill=0)
        draw.ellipse([(x+28, y+16), (x+42, y+30)], fill=0)
        draw.rectangle([(x+12, y+24), (x+34, y+32)], fill=0)
        if code in (61, 63, 65, 80, 81, 82, 51, 53, 55):
            for i in range(3):
                draw.line([(x+16+i*10, y+36), (x+12+i*10, y+46)], fill=0, width=2)
        elif code in (71, 73, 75, 85, 86):
            for i in range(3):
                cx = x + 16 + i*10
                draw.line([(cx-4, y+40), (cx+4, y+40)], fill=0, width=2)
                draw.line([(cx, y+36), (cx, y+44)], fill=0, width=2)
        elif code in (95, 96, 99):
            draw.polygon([(x+24, y+32), (x+16, y+44), (x+22, y+44), (x+18, y+54), (x+30, y+40), (x+24, y+40)], fill=0)

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
            t_str = f"{s_loc.strftime('%H:%M')}"
            if isinstance(dtend, datetime):
                t_str += f"–{dtend.astimezone(TZ).strftime('%H:%M')}"
            parsed.append((s_loc.hour * 60 + s_loc.minute, t_str, summary))
    return sorted(parsed, key=lambda x: (x[0], x[2]))

# --- Bild erstellen ---
now = datetime.now(TZ)
img = Image.new("L", (WIDTH, HEIGHT), 255)
draw = ImageDraw.Draw(img)

# Header
date_str = f"{WOCHENTAGE[now.weekday()]}, {now.day}. {MONATE[now.month-1]}"
draw.text((30, 22), date_str, fill=0, font=f_title)
time_str = now.strftime("%H:%M")
draw.text((WIDTH - 30 - draw.textlength(time_str, font=f_title), 22), time_str, fill=0, font=f_title)
draw.line([(30, 70), (WIDTH-30, 70)], fill=0, width=2)

# Wetter-Sektion
draw.text((30, 88), "WETTER", fill=0, font=f_section)
draw.text((WIDTH - 30 - draw.textlength(LOCATION_NAME, font=f_small), 92), LOCATION_NAME, fill=80, font=f_small)

print("2/4 Lade Wetterdaten...")
url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,precipitation_probability,weather_code&timezone={TIMEZONE_STR}&forecast_days=1"
try:
    hourly = requests.get(url, timeout=12).json().get("hourly", {})
    times = hourly.get("time", [])
except:
    hourly = {}
    times = []

periods = [("Morgens", "08:00"), ("Mittags", "13:00"), ("Abends", "19:00")]
card_w = (WIDTH - 80) // 3

for i, (label, t_target) in enumerate(periods):
    x = 30 + i * (card_w + 10)
    idx = next((k for k, t in enumerate(times) if t.endswith(t_target)), 0)
    code = hourly.get("weather_code", [3])[idx] if times else 3
    temp = round(hourly.get("temperature_2m", [0])[idx]) if times else 0
    rain = hourly.get("precipitation_probability", [0])[idx] if times else 0

    # Karte
    draw.rounded_rectangle([(x, 125), (x+card_w-10, 290)], radius=12, outline=0, width=2)
    draw.text((x+12, 135), label.upper(), fill=60, font=f_label)
    draw_icon(draw, x+12, 160, code, 56)
    draw.text((x+78, 168), f"{temp}°", fill=0, font=f_temp)
    desc = WMO_CODES.get(code, "Bedeckt")
    draw.text((x+12, 230), desc, fill=0, font=f_small)
    draw.text((x+12, 252), f"{rain}% Regen", fill=80, font=f_tiny)

# Kalender
print("3/4 Lade Kalenderdaten...")
cal = None
if ICAL_URL:
    try:
        cal = Calendar.from_ical(requests.get(ICAL_URL, timeout=15).text)
    except:
        cal = None

tomorrow = now.date() + timedelta(days=1)
sections = [
    ("HEUTE", get_events(cal, now.date())),
    (f"MORGEN · {WOCHENTAGE[tomorrow.weekday()]} {tomorrow.day}.{tomorrow.month:02d}.", get_events(cal, tomorrow))
]

y = 320
for s_idx, (title, ev_list) in enumerate(sections):
    draw.text((30, y), title, fill=0, font=f_section)
    y += 38
    if not ev_list:
        draw.text((40, y), "Keine Termine", fill=100, font=f_regular)
        y += 40
    else:
        for _, t_str, summary in ev_list[:6]:
            if y > HEIGHT - 50:
                break
            # Zeit links
            draw.text((30, y), t_str, fill=0, font=f_regular)
            # Titel
            max_w = WIDTH - 220
            while len(summary) > 2 and draw.textlength(summary, font=f_regular) > max_w:
                summary = summary[:-2] + "…"
            draw.text((190, y), summary, fill=0, font=f_regular)
            y += 34
            draw.line([(30, y-6), (WIDTH-30, y-6)], fill=220, width=1)
    if s_idx == 0:
        y += 10
        draw.line([(30, y), (WIDTH-30, y)], fill=0, width=1)
        y += 18

img.save("dashboard.png", "PNG")
print("4/4 Fertig: dashboard.png gespeichert!")
