import os
import re
from dotenv import load_dotenv
from langchain.agents import initialize_agent, Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pytz
from dateutil.parser import parse
from backend.calendar_utils import check_availability, book_slot

load_dotenv()

SERVICE_ACCOUNT_FILE = 'service_account.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = os.getenv('CALENDAR_ID')

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7
)

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('calendar', 'v3', credentials=credentials)

def ensure_timezone(dt_string, default_tz='Asia/Kolkata'):
    """
    Ensures the datetime string has a timezone offset.
    If missing, assumes the default_tz.
    """
    try:
        dt = parse(dt_string)
        if dt.tzinfo is None:
            tz = pytz.timezone(default_tz)
            dt = tz.localize(dt)
        return dt.isoformat()
    except Exception as e:
        print(f"Error in ensure_timezone for '{dt_string}': {e}")
        return dt_string

def extract_summary_from_text(user_input: str) -> str:
    """
    Dynamically extracts a summary from the user input by removing time/date phrases.
    """
    text = re.sub(r'\b(at|from|to)\b\s*\d{1,2}(:\d{2})?\s*(am|pm)?', '', user_input, flags=re.IGNORECASE)
    text = re.sub(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', '', text)
    text = re.sub(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b\s*\d{1,2}(st|nd|rd|th)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'for\s+\d+\s*hour[s]?', '', text, flags=re.IGNORECASE)
    summary = text.strip(" ,.")
    if len(summary) < 3:
        return "Appointment"
    return summary

def extract_booking_details(user_input: str) -> dict:
    """
    Uses the LLM to extract structured booking details from natural language input.
    Returns a dict with keys: start_time, end_time, summary.
    """
    extraction_prompt = (
        "Extract the following details from this booking request. "
        "Return your answer as JSON with keys: start_time (ISO 8601), end_time (ISO 8601), summary (a concise description of the event). "
        "If any detail is missing, use null. "
        "If the date is given in DD-MM-YYYY or similar format, convert it to ISO 8601. "
        "Request: " + user_input
    )
    try:
        response = llm.invoke(extraction_prompt)
    except Exception as e:
        return {"error": f"LLM error: {e}"}
    import json
    try:
        resp = response.strip()
        if resp.startswith("```"):
            resp = resp.lstrip("`")
            if resp.lower().startswith("json"):
                resp = resp[4:].strip()
            if resp.endswith("```"):
                resp = resp[:-3].strip()
        details = json.loads(resp)
        return details
    except Exception:
        from datetime import datetime, timedelta
        date_match = re.search(r'(\d{2}-\d{2}-\d{4})', user_input)
        time_match = re.search(r'(\d{1,2}:\d{2}\s?(?:am|pm)?)', user_input, re.IGNORECASE)
        duration_match = re.search(r'for\s+(\d+)\s*hour', user_input)
        if date_match and time_match:
            date_str = date_match.group(1)
            time_str = time_match.group(1)
            try:
                start = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %I:%M %p")
            except ValueError:
                start = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
            duration = int(duration_match.group(1)) if duration_match else 1
            end = start + timedelta(hours=duration)
            summary = extract_summary_from_text(user_input)
            return {
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "summary": summary
            }
        return {}

def book_slot_wrapper(user_input: str):
    details = extract_booking_details(user_input)
    start_time = details.get("start_time")
    end_time = details.get("end_time")
    summary = details.get("summary") or extract_summary_from_text(user_input)
    if not (start_time and end_time):
        return "Sorry, I couldn't extract the required time details from your request."
    try:
        return book_slot(start_time, end_time, summary)
    except Exception as e:
        return f"Error booking slot: {str(e)}"

def check_availability_wrapper(user_input: str):
    details = extract_booking_details(user_input)
    start_time = details.get("start_time")
    end_time = details.get("end_time")
    if not (start_time and end_time):
        return "Sorry, I couldn't extract the required time details from your request."
    try:
        return check_availability(start_time, end_time)
    except Exception as e:
        print(f"Error in check_availability: {e}")
        return f"Error checking availability: {e}"

tools = [
    Tool(
        name="CheckAvailability",
        func=check_availability_wrapper,
        description="Checks Google Calendar for available slots. Input can be a date or time range."
    ),
    Tool(
        name="BookSlot",
        func=book_slot_wrapper,
        description="Books a slot in Google Calendar. Input can be natural language (e.g., 'Book a meeting with my friend at 3:00 pm to 4:00 pm at 04-07-2025')."
    ),
]

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent_type="zero-shot-react-description"
)

def chat_with_agent(msg, session_id=None):
    try:
        return agent.invoke(msg)
    except Exception as e:
        print(f"Error in agent.invoke: {e}")
        return {"response": "Sorry, there was an error processing your request. Please try again later."}
