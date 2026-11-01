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
WOCHENTAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
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
f_temp = ImageFont.truetype(font_b, 44)
f_medium = ImageFont.truetype(font_b, 20)
f_w_desc = ImageFont.truetype(font_p, 20)
f_regular = ImageFont.truetype(font_p, 18)
f_w_small = ImageFont.truetype(font_p, 16)
f_small = ImageFont.truetype(font_p, 14)
f_quote = ImageFont.truetype(font_p, 20)
f_quote_author = ImageFont.truetype(font_p, 16)

def draw_icon(draw, x, y, code):
    def cloud(cx, cy):
        for dx, dy, r in [(16, 24, 11), (28, 17, 14), (41, 24, 11)]:
            draw.ellipse([(cx+dx-r, cy+dy-r), (cx+dx+r, cy+dy+r)], fill=255, outline=0, width=3)
        draw.rectangle([(cx+16, cy+21), (cx+41, cy+35)], fill=255)
        draw.line([(cx+13, cy+35), (cx+44, cy+35)], fill=0, width=3)

    if code in (0, 1):
        for dx, dy in [(21, 0), (0, 21), (15, 15), (-15, 15)]:
            draw.line([(x+27-dx, y+27-dy), (x+27+dx, y+27+dy)], fill=0, width=3)
        draw.ellipse([(x+12, y+12), (x+42, y+42)], fill=255)
        draw.ellipse([(x+16, y+16), (x+38, y+38)], fill=255, outline=0, width=3)
    elif code == 2:
        draw.ellipse([(x+27, y+5), (x+46, y+24)], fill=255, outline=0, width=3)
        cloud(x, y+8)
    elif code in (45, 48):
        for dy in (16, 27, 38):
            draw.line([(x+8, y+dy), (x+48, y+dy)], fill=0, width=3)
    else:
        cloud(x, y)
        if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
            for rx in (18, 28, 39):
                draw.line([(x+rx, y+40), (x+rx-4, y+51)], fill=0, width=3)
        elif code in (71, 73, 75, 77, 85, 86):
            for sx in (18, 28, 39):
                draw.line([(x+sx-4, y+46), (x+sx+4, y+46)], fill=0, width=2)
                draw.line([(x+sx, y+42), (x+sx, y+50)], fill=0, width=2)
        elif code in (95, 96, 99):
            draw.polygon([(x+30, y+36), (x+20, y+47), (x+27, y+47), (x+23, y+56), (x+36, y+43), (x+28, y+43)], fill=0)

def get_events_for_day(cal, target_date):
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
            t_str = f"{s_loc.strftime('%H:%M')} - {dtend.astimezone(TZ).strftime('%H:%M')}" if isinstance(dtend, datetime) else f"{s_loc.strftime('%H:%M')} Uhr"
            parsed.append((s_loc.hour * 60 + s_loc.minute, t_str, summary))
    return sorted(parsed, key=lambda x: (x[0], x[2]))

def get_events_for_range(cal, start_date, end_date):
    all_events = []
    cur = start_date
    while cur <= end_date:
        prefix = f"{WOCHENTAGE_KURZ[cur.weekday()]}, {cur.day:02d}.{cur.month:02d}."
        for sort_k, t_str, summary in get_events_for_day(cal, cur):
            all_events.append((sort_k, f"{prefix} | {t_str}", summary))
        cur += timedelta(days=1)
    return all_events

def get_daily_quote():
    try:
        data = requests.get("https://api.zitat-service.de/v1/quote?language=de", timeout=10).json()
        q, a = data.get("quote", "").strip(), data.get("authorName", "").strip()
        if q:
            return q, a
    except Exception:
        pass
    return "Der beste Weg, die Zukunft vorherzusagen, ist, sie zu gestalten.", "Peter Drucker"

def wrap_text(draw_obj, text, font, max_w):
    lines, cur = [], ""
    for w in text.split():
        test = f"{cur} {w}".strip()
        if draw_obj.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

now = datetime.now(TZ)
img = Image.new("L", (WIDTH, HEIGHT), 255)
draw = ImageDraw.Draw(img)

# Schwarzer Balken oben
BAR_HEIGHT, GAP = 42, 10
TOP = BAR_HEIGHT + GAP
draw.rectangle([(0, 0), (WIDTH, BAR_HEIGHT)], fill=0)

# 1. Header
date_str = f"{WOCHENTAGE[now.weekday()]}, {now.day}. {MONATE[now.month - 1]} {now.year}"
draw.text((30, TOP), date_str, fill=0, font=f_large)
draw.line([(30, TOP + 48), (WIDTH - 30, TOP + 48)], fill=180, width=2)

# 2. Wetter (Vergrößert & rechtsbündig bis zum Rand verteilt)
print("2/4 Lade Wetterdaten...")
w_start = TOP + 62
draw.text((30, w_start), f"WETTER HEUTE – {LOCATION_NAME.upper()}", fill=0, font=f_medium)
upd_str = f"Stand: {now.strftime('%H:%M')} Uhr"
draw.text((WIDTH - 30 - draw.textlength(upd_str, font=f_small), w_start + 5), upd_str, fill=90, font=f_small)

url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,precipitation_probability,weather_code&timezone={TIMEZONE_STR}&forecast_days=1"
try:
    hourly = requests.get(url, timeout=12).json().get("hourly", {})
    times = hourly.get("time", [])
except Exception:
    hourly, times = {}, []

slots_data = []
for label, t_target in [("Morgens (08:00)", "08:00"), ("Mittags (13:00)", "13:00"), ("Abends (19:00)", "19:00")]:
    idx = next((k for k, t in enumerate(times) if t.endswith(t_target)), 0)
    code = hourly.get("weather_code", [3])[idx] if times else 3
    temp = f"{round(hourly.get('temperature_2m', [0])[idx])}°C" if times else "–"
    rain = f"{hourly.get('precipitation_probability', [0])[idx]}% Regen" if times else ""
    desc = WMO_CODES.get(code, "Bedeckt")
    col_w = max(
        62 + draw.textlength(temp, font=f_temp),
        draw.textlength(desc, font=f_w_desc),
        draw.textlength(label, font=f_w_small),
        draw.textlength(rain, font=f_w_small)
    )
    slots_data.append((label, code, temp, desc, rain, col_w))

x_positions = [
    30,
    int((WIDTH - slots_data[1][5]) // 2),
    int(WIDTH - 30 - slots_data[2][5])
]

for x, (label, code, temp, desc, rain, _) in zip(x_positions, slots_data):
    draw.text((x, w_start + 38), label, fill=90, font=f_w_small)
    draw_icon(draw, x, w_start + 64, code)
    draw.text((x + 62, w_start + 66), temp, fill=0, font=f_temp)
    draw.text((x, w_start + 126), desc, fill=0, font=f_w_desc)
    draw.text((x, w_start + 154), rain, fill=90, font=f_w_small)

draw.line([(30, w_start + 188), (WIDTH - 30, w_start + 188)], fill=180, width=2)

# 3. Zitat vorab berechnen (dynamisch am unteren Rand verankert)
quote, author = get_daily_quote()
quote_lines = wrap_text(draw, f"„{quote}“", f_quote, WIDTH - 80)[:3]
quote_block_h = len(quote_lines) * 26 + (24 if author else 0)
quote_y = HEIGHT - 18 - quote_block_h
quote_line_y = quote_y - 14

# 4. Kalender
print("3/4 Lade Kalenderdaten...")
cal = None
if ICAL_URL:
    try:
        cal = Calendar.from_ical(requests.get(ICAL_URL, timeout=15).text)
    except Exception:
        cal = None

today_date = now.date()
start_r = today_date + timedelta(days=1)
if today_date.weekday() == 6:
    end_r = today_date + timedelta(days=7)
    r_title = f"TERMINE FOLGENDE WOCHE ({start_r.day:02d}.{start_r.month:02d}. – {end_r.day:02d}.{end_r.month:02d}.)"
else:
    end_r = today_date + timedelta(days=6 - today_date.weekday())
    r_title = f"TERMINE RESTLICHE WOCHE (bis So, {end_r.day:02d}.{end_r.month:02d}.)"

sections = [
    ("TERMINE HEUTE", get_events_for_day(cal, today_date), 195, 6),
    (r_title, get_events_for_range(cal, start_r, end_r), 290, 10)
]

y = w_start + 208
for s_idx, (title, ev_list, text_x, max_items) in enumerate(sections):
    draw.text((30, y), title, fill=0, font=f_medium)
    y += 36
    if not ev_list:
        draw.text((30, y), "Keine Termine eingetragen.", fill=90, font=f_regular)
        y += 36
    for _, t_str, summary in ev_list[:max_items]:
        if y > quote_line_y - 36:
            break
        draw.text((30, y), t_str, fill=0, font=f_regular)
        max_w = WIDTH - text_x - 30
        while len(summary) > 3 and draw.textlength(summary, font=f_regular) > max_w:
            summary = summary[:-2] + "…"
        draw.text((text_x, y), summary, fill=0, font=f_regular)
        y += 36
        draw.line([(30, y - 7), (WIDTH - 30, y - 7)], fill=230, width=1)
    if s_idx == 0:
        y += 12
        draw.line([(30, y), (WIDTH - 30, y)], fill=180, width=2)
        y += 20

# 5. Zitat unten zeichnen
draw.line([(30, quote_line_y), (WIDTH - 30, quote_line_y)], fill=180, width=1)
for line in quote_lines:
    draw.text((40, quote_y), line, fill=0, font=f_quote)
    quote_y += 26
if author:
    draw.text((40, quote_y + 2), f"— {author}", fill=80, font=f_quote_author)

img.save("dashboard.png", "PNG")
print("4/4 Fertig!")
