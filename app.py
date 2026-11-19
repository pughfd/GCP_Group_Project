import os
import re
from datetime import datetime, timedelta, timezone
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# load API keys from .env
load_dotenv()

# init flask
app = Flask(__name__)
app.json.ensure_ascii = False

# set api keys
TICKETMASTER_API_KEY = os.environ.get("TICKETMASTER_API_KEY")
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY")

# weather codes
WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


## GET EVENTS FROM TICKETMASTER USING DISCOVERY API
def fetch_ticketmaster_events(city: str, state_code: str | None = None) -> list[dict]:
    """Fetches upcoming events from Ticketmaster Discovery API (adapted from agent.py)."""
    # if no api key return nothing
    if not TICKETMASTER_API_KEY:
        return []

    # get the current time and start and end bounds for search (14 days)
    now = datetime.now(timezone.utc)
    start_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date = (now + timedelta(days=14)).strftime("%Y-%m-%dT23:59:59Z")

    # url construction
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "city": city,
        "countryCode": "US",
        "startDateTime": start_date,
        "endDateTime": end_date,
        "size": 50,
        "sort": "date,asc",
    }

    # only add stateCode if the user provided one (e.g., "Richmond, VA")
    if state_code:
        params["stateCode"] = state_code

    # try accessing ticketmaster api
    # if can't - return nothing
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        app.logger.error(f"Ticketmaster API error: {e}")
        return []
    
    # if the api is accessible...
    events = data.get("_embedded", {}).get("events", [])
    cleaned = []

    # loop through all returned events
    for event in events:
        # ticketmaster api returns a lot of junk we don't need
        # this pulls out only the things we do need and returns it

        # this will return name, date, time, venue, category,
        # source (always ticketmaster), and the url for the event
        venue_info = event.get("_embedded", {}).get("venues", [{}])[0]
        classifications = event.get("classifications", [{}])[0]
        start_info = event.get("dates", {}).get("start", {})
        raw_cat = classifications.get("segment", {}).get("name", "Event")
        category = "Event" if not raw_cat or raw_cat == "Undefined" else raw_cat

        cleaned.append({
            "name": event.get("name", "Untitled Event").strip(),
            "date": start_info.get("localDate", "TBA"),
            "time": start_info.get("localTime", "TBA"),
            "venue": venue_info.get("name", "Unknown Venue").strip(),
            "category": category,
            "source": "Ticketmaster",
            "url": event.get("url", ""),
        })
    return cleaned

## CONVERTS SERPAPI 'WHEN' STRINGS INTO YYYY-MM-DD HH:MM
def parse_serpapi_date(when_str: str) -> tuple[str, str]:
    """Converts SerpAPI 'when' strings (e.g., 'Fri, Nov 13, 8:00 PM') into YYYY-MM-DD and HH:MM"""
    # if there is no 'when' str, return 'tba'
    if not when_str:
        return "TBA", "TBA"

    current_year = datetime.now().year
    # match patterns like 'Nov 13' or 'Nov 13, 2026' using regex
    date_match = re.search(r"([A-Za-z]{3})\s+(\d{1,2})(?:,\s*(\d{4}))?", when_str)
    time_match = re.search(r"(\d{1,2}:\d{2}\s*[APap][Mm])", when_str)

    # placeholder date value set
    parsed_date = "TBA"

    # if a date was found in the regex search...
    if date_match:
        # assign month, day, and year to different variables based on regex groups
        month_str, day_str, year_str = date_match.groups()

        # set the year variable by checking if year_str is truthy
        # if yes, convert to an int and assign it to 'year'
        # if no, fall back to current_year instead
        year = int(year_str) if year_str else current_year

        # try parsing the date variables into a datetime object
        try:
            dt = datetime.strptime(f"{month_str} {day_str} {year}", "%b %d %Y")
            today_buffered = (datetime.now(timezone.utc) - timedelta(hours=12)).date()
            if not year_str and dt.date() < today_buffered:
                dt = dt.replace(year=year + 1)
            parsed_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # placeholder time value set
    parsed_time = "TBA"

    # if a time was found in the regex search...
    if time_match:
        # try parsing the time variables into a datetime object
        try:
            t_dt = datetime.strptime(time_match.group(1).upper().replace(" ", ""), "%I:%M%p")
            parsed_time = t_dt.strftime("%H:%M:%S")
        except ValueError:
            parsed_time = time_match.group(1)

    # return date and time
    return parsed_date, parsed_time

## FETCHES LOCAL EVENTS VIA THE SERPAPI (GOOGLE EVENTS)
def fetch_serpapi_events(city: str) -> list[dict]:
    """Fetches upcoming events via SerpAPI Google Events engine."""
    # if you don't have an api key return nothing
    if not SERPAPI_API_KEY:
        return []

    # setting api params
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_events",
        "q": f"Events in {city}",
        "htichips": "date:week",
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_API_KEY,
    }

    # try accessing the api
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        app.logger.error(f"SerpAPI error: {e}")
        return []

    # take the api data and grab only what is needed, return cleaned object
    events = data.get("events_results", [])
    cleaned = []
    for event in events:
        when_str = event.get("date", {}).get("when", "")
        parsed_date, parsed_time = parse_serpapi_date(when_str)
        venue_name = event.get("venue", {}).get("name")
        if not venue_name:
            address = event.get("address", [])
            venue_name = address[0] if address else "Unknown Venue"

        ticket_info = event.get("ticket_info", [])
        event_url = event.get("link") or (ticket_info[0].get("link", "") if ticket_info else "")
        
        cleaned.append({
            "name": event.get("title", "Untitled Event").strip(),
            "date": parsed_date,
            "time": parsed_time,
            "venue": venue_name.strip(),
            "category": "Local Event",
            "source": "Google Events",
            "url": event_url,
        })
    return cleaned

## FETCHES LOCAL WEATHER DATA FROM OPEN-METEO
def fetch_weather_by_date(city: str) -> dict[str, str]:
    """Geocodes the city and fetches a 14-day daily forecast from Open-Meteo."""
    # try the api
    try:
        geo_resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
                "countryCode": "US",
            },
            timeout=5,
        )
        geo_resp.raise_for_status()
        results = geo_resp.json().get("results")
        if not results:
            return {}

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]

        # get weather forecast
        weather_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "weathercode,temperature_2m_max,temperature_2m_min",
                "temperature_unit": "fahrenheit",
                "timezone": "auto",
                "forecast_days": 14,
            },
            timeout=5,
        )
        # get api response and parse needed info
        weather_resp.raise_for_status()
        daily = weather_resp.json().get("daily", {})

        dates = daily.get("time", [])
        codes = daily.get("weathercode", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])

        forecast_map = {}
        for d, code, high, low in zip(dates, codes, highs, lows):
            desc = WMO_WEATHER_CODES.get(code, "Forecast available")
            forecast_map[d] = f"{desc} ({round(high)}°F / {round(low)}°F)"
        return forecast_map
    except requests.RequestException as e:
        app.logger.error(f"Open-Meteo error: {e}")
        return {}

## BUILD A DEDUPE FINGERPRINT FROM CLEANED TITLES/DATES/VENUES
def normalize_key(event: dict) -> tuple[str, str, str]:
    """Builds a deduplication fingerprint from cleaned title, date, and venue prefix."""
    clean_title = re.sub(r"[^a-z0-9\s]", "", event["name"].lower())
    # drop trailing tour/subtitle noise after common separators
    clean_title = re.split(
        r"\s+(?:tour|live|at|presents|the\s+musical|musical)\b",
        clean_title,
    )[0].strip()
    clean_venue = re.sub(r"[^a-z0-9\s]", "", event["venue"].lower()).split()
    venue_token = clean_venue[0] if clean_venue else ""
    return (clean_title, event["date"], venue_token)

## MERGE EVENT LISTS, REMOVE DUPES, ADD WEATHER, SORT BY DATE
def merge_and_dedupe(tm_events: list[dict], serp_events: list[dict], weather_map: dict[str, str]) -> list[dict]:
    """Merges event lists, removes duplicates, enriches with weather, and sorts by date."""
    seen = {}

    for event in tm_events + serp_events:
        key = normalize_key(event)
        if key in seen:
            existing = seen[key]
            if event["source"] != existing["source"]:
                if event["source"] not in existing["source"]:
                    existing["source"] = f"{existing['source']} + {event['source']}"
                continue
            elif event["time"] != existing["time"]:
                key = (*key, event["time"])
            else:
                # Same source and same start time — true duplicate, keep the first one
                continue

        event["weather"] = weather_map.get(event["date"], "Forecast unavailable")
        seen[key] = event

    today_str = (datetime.now(timezone.utc) - timedelta(hours=12)).strftime("%Y-%m-%d")
    merged = [
        e for e in seen.values()
        if e["date"] == "TBA" or e["date"] >= today_str
    ]
    merged.sort(key=lambda e: (e["date"] == "TBA", e["date"], e["time"]))
    return merged

def parse_city_state(raw_city: str) -> tuple[str, str | None]:
    parts = [p.strip() for p in raw_city.split(",", 1)]
    city_name = parts[0]
    state_code = parts[1].upper() if len(parts) > 1 and len(parts[1]) == 2 else None
    return city_name, state_code

@app.route("/health")
def health():
    return "OK", 200

@app.route("/")
def index():
    if os.path.exists(os.path.join(app.template_folder or "templates", "index.html")):
        return render_template("index.html")
    return (
        "<h2> City Events Finder Backend Running</h2>"
        "<p>Try <code>/health</code> or <code>/api/events?city=Richmond</code></p>"
    )

@app.route("/api/events")
def get_events():
    raw_city = request.args.get("city", "").strip()
    if not raw_city:
        return jsonify({"error": "Please provide a 'city' query parameter."}), 400

    city_name, state_code = parse_city_state(raw_city)

    tm_events = fetch_ticketmaster_events(city_name, state_code)
    serp_events = fetch_serpapi_events(raw_city)
    weather_map = fetch_weather_by_date(raw_city)

    results = merge_and_dedupe(tm_events, serp_events, weather_map)
    return jsonify({
        "city": raw_city,
        "count": len(results),
        "events": results,
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
