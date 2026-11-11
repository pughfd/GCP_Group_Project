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
def fetch_ticketmaster_events(city: str) -> list[dict]:
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
        "startDateTime": start_date,
        "endDateTime": end_date,
        "size": 20,
        "sort": "date,asc",
    }

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

        cleaned.append({
            "name": event.get("name", "Untitled Event"),
            "date": start_info.get("localDate", "TBA"),
            "time": start_info.get("localTime", "TBA"),
            "venue": venue_info.get("name", "Unknown Venue"),
            "category": classifications.get("segment", {}).get("name", "Event"),
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

