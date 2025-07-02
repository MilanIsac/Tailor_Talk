import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime
from dateutil.parser import parse
import pytz

load_dotenv()

# SERVICE_ACCOUNT_FILE = 'service_account.json'
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_JSON")
if not SERVICE_ACCOUNT_FILE:
    raise ValueError("Missing GOOGLE_SERVICE_JSON")
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = os.getenv('CALENDAR_ID')

print("Loaded CALENDAR_ID:", CALENDAR_ID)

if not CALENDAR_ID:
    raise ValueError("CALENDAR_ID is not set in .env file.")

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('calendar', 'v3', credentials=credentials)

def ensure_timezone(dt_string, default_tz='Asia/Kolkata'):
    """
    Ensures the datetime string has a timezone offset.
    If missing, assumes the default_tz.
    """
    try:
        dt = datetime.fromisoformat(dt_string)
        if dt.tzinfo is None:
            tz = pytz.timezone(default_tz)
            dt = tz.localize(dt)
        return dt.isoformat()
    except Exception as e:
        print(f"Error in ensure_timezone for '{dt_string}': {e}")
        return dt_string

def check_availability(start_time, end_time):
    """
    Checks if the time slot is available on the calendar.
    start_time, end_time: ISO 8601 strings (with or without timezone)
    """
    try:
        start_time = ensure_timezone(start_time)
        end_time = ensure_timezone(end_time)
        events = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        if not events['items']:
            return "Slot is available."
        return "Slot is not available."
    except Exception as e:
        print(f"Error in check_availability: {e}")
        return f"Error checking availability: {e}"


def book_slot(start_time, end_time, summary):
    """
    Books a slot in the calendar if available.
    If the slot is occupied, returns the summary of the conflicting event(s).
    """
    try:
        start_time = ensure_timezone(start_time)
        end_time = ensure_timezone(end_time)
        # Fetch events in the requested window
        events = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        requested_start = parse(start_time)
        requested_end = parse(end_time)
        conflicting_events = []
        for event in events.get('items', []):
            event_start = parse(event['start'].get('dateTime', event['start'].get('date')))
            event_end = parse(event['end'].get('dateTime', event['end'].get('date')))
            # Check for overlap
            if requested_start < event_end and event_start < requested_end:
                conflicting_events.append(event.get('summary', 'No Title'))
        if conflicting_events:
            if len(conflicting_events) == 1:
                return f"Error: The time slot is occupied by: {conflicting_events[0]}"
            else:
                return "Error: The time slot is occupied by: " + ", ".join(conflicting_events)
        # If no conflicts, book the event
        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_time, 'timeZone': 'Asia/Kolkata'},
        }
        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return f"Your appointment has been booked. You can view it here: {event.get('htmlLink')}"
    except Exception as e:
        print(f"Error in book_slot: {e}")
        return f"Error booking slot: {e}"