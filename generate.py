import os
from datetime import datetime, time
from zoneinfo import ZoneInfo
import requests
from PIL import Image, ImageDraw, ImageFont
from icalendar import Calendar
import recurring_ical_events

TIMEZONE_STR = os.getenv("TIMEZONE", "Europe/Berlin")
TZ = ZoneInfo(TIMEZONE_STR)
LAT = os.getenv("LATITUDE", "48.96")
LON = os.getenv("LONGITUDE", "9.13")
ICAL_URL = os.getenv("ICAL_URL", "")

WIDTH, HEIGHT = 758, 1024
BG_COLOR = 255  # Weiß
TEXT_COLOR = 0  # Schwarz
LINE_COLOR = 180  # Grau

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
        font_large = ImageFont.truetype(font_bold_path, 34)
        font_medium = ImageFont.truetype(font_bold_path, 22)
        font_regular = ImageFont.truetype(font_path, 18)
        font_small = ImageFont.truetype(font_path, 14)
    except IOError:
        font_large = font_medium = font_regular = font_small = ImageFont.load_default()
    return font_large, font_medium, font_regular, font_small

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
            rain = hourly["precipitation_probability"][match_idx]
            code = hourly["weather_code"][match_idx]
            weather_data[label] = {
                "temp": f"{temp}°C",
                "rain": f"{rain}% Regen",
                "desc": WMO_CODES.get(code, "Unbekannt")
            }
        else:
            weather_data[label] = {"temp": "--", "rain": "--", "desc": "--"}
    return weather_data

def fetch_calendar_events(now):
    if not ICAL_URL:
        return []
    
    start_of_day = datetime.combine(now.date(), time.min).replace(tzinfo=TZ)
    end_of_day = datetime.combine(now.date(), time.max).replace(tzinfo=TZ)
    
    try:
        raw_ics = requests.get(ICAL_URL, timeout=15).text
        cal = Calendar.from_ical(raw_ics)
        events = recurring_ical_events.of(cal).between(start_of_day, end_of_day)
        
        parsed = []
        for event in events:
            summary = str(event.get("SUMMARY", "Ohne Titel"))
            dtstart = event.get("DTSTART").dt
            
            if not isinstance(dtstart, datetime):
                time_str = "Ganztägig"
                sort_key = 0
            else:
                dtstart_local = dtstart.astimezone(TZ)
                time_str = dtstart_local.strftime("%H:%M")
                sort_key = dtstart_local.hour * 60 + dtstart_local.minute
                
            parsed.append((sort_key, time_str, summary))
            
        parsed.sort(key=lambda x: x[0])
        return parsed
    except Exception as e:
        return [(0, "Fehler", f"Kalenderabruf fehlgeschlagen: {str(e)[:30]}")]

def render_dashboard():
    now = datetime.now(TZ)
    img = Image.new("L", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    f_large, f_medium, f_regular, f_small = load_fonts()
    
    date_str = now.strftime("%A, %d. %B %Y")
    update_str = f"Stand: {now.strftime('%H:%M')} Uhr"
    draw.text((30, 30), date_str, fill=TEXT_COLOR, font=f_large)
    draw.text((WIDTH - 190, 42), update_str, fill=TEXT_COLOR, font=f_small)
    draw.line([(30, 80), (WIDTH - 30, 80)], fill=LINE_COLOR, width=2)
    
    draw.text((30, 100), "WETTER HEUTE", fill=TEXT_COLOR, font=f_medium)
    weather = fetch_weather()
    col_width = (WIDTH - 60) // 3
    
    for i, (slot, data) in enumerate(weather.items()):
        x = 30 + i * col_width
        draw.text((x, 140), slot, fill=TEXT_COLOR, font=f_regular)
        draw.text((x, 170), data["temp"], fill=TEXT_COLOR, font=f_large)
        draw.text((x, 215), data["desc"], fill=TEXT_COLOR, font=f_small)
        draw.text((x, 235), data["rain"], fill=TEXT_COLOR, font=f_small)
        
    draw.line([(30, 275), (WIDTH - 30, 275)], fill=LINE_COLOR, width=2)
    
    draw.text((30, 295), "TERMINE HEUTE", fill=TEXT_COLOR, font=f_medium)
    events = fetch_calendar_events(now)
    
    y = 345
    if not events:
        draw.text((30, y), "Keine Termine für heute eingetragen.", fill=TEXT_COLOR, font=f_regular)
    else:
        for _, time_str, summary in events[:12]:
            draw.text((30, y), time_str, fill=TEXT_COLOR, font=f_regular)
            display_title = summary if len(summary) <= 38 else summary[:35] + "..."
            draw.text((160, y), display_title, fill=TEXT_COLOR, font=f_regular)
            y += 42
            draw.line([(30, y - 10), (WIDTH - 30, y - 10)], fill=230, width=1)
            
    img.save("dashboard.png", "PNG")

if __name__ == "__main__":
    render_dashboard()
