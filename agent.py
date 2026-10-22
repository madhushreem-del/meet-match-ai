"""
Meet Match AI agent workflow.
Uses synthetic calendar data and stores newly confirmed bookings in bookings.json.
Invitation delivery is simulated; no real invitations are sent.
"""
import json
import os
import uuid
import streamlit as st
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google import genai
from scheduler import find_available_slots

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    try:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        API_KEY = None
client = genai.Client(api_key=API_KEY) if API_KEY else None
BOOKINGS_FILE = Path(__file__).with_name("bookings.json")


def understand_request(user_request):
    """Extract structured meeting details from a natural-language request."""
    if client is None:
        raise ValueError("Gemini API key is missing. Check your .env file.")

    prompt = f"""
You are Meet Match AI, a meeting scheduling assistant.
Return ONLY valid JSON with these keys:
meeting_date, duration_minutes, attendee_names, preferred_start, preferred_end.
Rules:
- Never invent attendee names.
- Resolve relative dates using today's date: {datetime.now().date().isoformat()}.
- If the date is clear, return meeting_date as YYYY-MM-DD.
- If the user says tomorrow afternoon, use tomorrow's date and a reasonable
  afternoon window such as preferred_start "13:00" and preferred_end "17:00".
- duration_minutes must be a number or null.
- Use attendee_names as a JSON array of names, or null if none are given.
- Use 24-hour HH:MM time format, or null if a time is not clear.
- Return null only when a field cannot reasonably be inferred.
- Do not confirm bookings or claim to have checked calendars.

User request:
{user_request}
"""
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
    )
    response_text = (response.text or "").strip()
    if response_text.startswith("```"):
        lines = response_text.splitlines()
        response_text = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        )
    details = json.loads(response_text)
    required_keys = {
        "meeting_date", "duration_minutes", "attendee_names",
        "preferred_start", "preferred_end",
    }
    if not isinstance(details, dict) or not required_keys.issubset(details):
        raise ValueError("Gemini returned incomplete meeting details.")
    return details


def find_meeting_options(
    meeting_date, attendee_ids, duration_minutes=45,
    work_start="09:00", work_end="17:00",
    preferred_start=None, preferred_end=None,
):
    return find_available_slots(
        meeting_date=meeting_date,
        attendee_ids=attendee_ids,
        duration_minutes=duration_minutes,
        work_start=work_start,
        work_end=work_end,
        preferred_start=preferred_start,
        preferred_end=preferred_end,
    )


def load_bookings():
    """Load locally created bookings. Existing sample bookings come from scheduler.py."""
    if not BOOKINGS_FILE.exists():
        return []
    try:
        with BOOKINGS_FILE.open("r", encoding="utf-8") as file:
            bookings = json.load(file)
        if not isinstance(bookings, list):
            raise ValueError("Booking data must be a JSON list.")
        return bookings
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError(
            "Could not read bookings.json. Check that it contains valid JSON."
        ) from error


def save_bookings(bookings):
    """Persist local bookings using a temporary file to reduce partial-write risk."""
    temporary_file = BOOKINGS_FILE.with_suffix(".json.tmp")
    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(bookings, file, indent=2)
    temporary_file.replace(BOOKINGS_FILE)


def _overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a


def check_availability(slot, attendee_ids):
    """Recheck scheduler availability and conflicts with locally saved bookings."""
    options = find_meeting_options(
        meeting_date=slot["date"],
        attendee_ids=attendee_ids,
        duration_minutes=int(slot["duration_minutes"]),
        work_start="09:00",
        work_end="17:00",
        preferred_start=slot["start"],
        preferred_end=slot["end"],
    )
    still_available = any(
        option["start"] == slot["start"]
        and option["end"] == slot["end"]
        and int(option["room_id"]) == int(slot["room_id"])
        for option in options
    )
    if not still_available:
        return False, "The selected slot is no longer available in the scheduler data."

    requested_attendees = {str(item) for item in attendee_ids}
    for booking in load_bookings():
        if booking.get("status") != "confirmed":
            continue
        if str(booking.get("date")) != str(slot["date"]):
            continue
        try:
            same_room = int(booking.get("room_id")) == int(slot["room_id"])
        except (TypeError, ValueError):
            same_room = False
        overlaps = _overlaps(
            str(slot["start"]), str(slot["end"]),
            str(booking.get("start", "00:00")), str(booking.get("end", "00:00")),
        )
        if same_room and overlaps:
            return False, "This room is already booked at that time."
        existing_attendees = {str(item) for item in booking.get("attendee_ids", [])}
        if existing_attendees.intersection(requested_attendees) and overlaps:
            return False, "An attendee has another confirmed meeting at that time."
    return True, "Availability rechecked successfully."


def book_meeting(slot, attendee_ids, approved=False):
    """Create a booking only after explicit human approval."""
    if not approved:
        return {
            "success": False,
            "message": "Booking not created: human approval is required.",
        }

    available, message = check_availability(slot, attendee_ids)
    if not available:
        return {"success": False, "message": message}

    bookings = load_bookings()
    signature = (
        str(slot["date"]), str(slot["start"]), str(slot["end"]),
        int(slot["room_id"]), tuple(sorted(str(x) for x in attendee_ids)),
    )
    for existing in bookings:
        try:
            existing_signature = (
                str(existing.get("date")), str(existing.get("start")),
                str(existing.get("end")), int(existing.get("room_id", -1)),
                tuple(sorted(str(x) for x in existing.get("attendee_ids", []))),
            )
        except (TypeError, ValueError):
            continue
        if existing_signature == signature and existing.get("status") == "confirmed":
            return {
                "success": False,
                "message": "This meeting already appears in your saved bookings.",
            }

    booking = {
        "booking_id": str(uuid.uuid4()),
        "date": str(slot["date"]),
        "start": str(slot["start"]),
        "end": str(slot["end"]),
        "room_id": int(slot["room_id"]),
        "room_name": str(slot["room_name"]),
        "attendee_ids": list(dict.fromkeys(attendee_ids)),
        "duration_minutes": int(slot["duration_minutes"]),
        "status": "confirmed",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    bookings.append(booking)
    save_bookings(bookings)
    return {
        "success": True,
        "booking": booking,
        "message": "Meeting room booking saved successfully.",
    }


def send_invitations(booking, simulate_failure=False):
    """Simulate invitation preparation; no real emails are sent."""
    if simulate_failure:
        return {
            "success": False,
            "message": "The room booking succeeded, but invitation preparation failed.",
        }
    return {
        "success": True,
        "message": (
            f"Simulated invitations prepared for {len(booking['attendee_ids'])} "
            "attendee(s). No real invitations were sent."
        ),
    }


def run_agent(slot, attendee_ids, approved=False, simulate_invite_failure=False):
    if not approved:
        return {
            "booking_success": False,
            "message": "Waiting for human approval. Nothing has been booked.",
        }
    result = book_meeting(slot=slot, attendee_ids=attendee_ids, approved=True)
    if not result["success"]:
        return {"booking_success": False, "message": result["message"]}
    invitation = send_invitations(
        result["booking"], simulate_failure=simulate_invite_failure
    )
    return {
        "booking_success": True,
        "booking": result["booking"],
        "invitation_success": invitation["success"],
        "message": result["message"] + " " + invitation["message"],
    }


if __name__ == "__main__":
    print("Meet Match AI agent is ready.")
    print("Gemini client is configured." if client else
          "Gemini API key is missing. Check your .env file.")
from agent import send_invitations

test_booking = {
    "attendee_ids": [1, 2, 3]
}

print(send_invitations(test_booking, simulate_failure=True))

def convert_london_time_to_utc(date_str, time_str):
    """
    Convert London local time to UTC, respecting daylight-saving time.
    """
    london = ZoneInfo("Europe/London")
    utc = ZoneInfo("UTC")

    local_time = datetime.strptime(
        f"{date_str} {time_str}",
        "%Y-%m-%d %H:%M"
    ).replace(tzinfo=london)

    return local_time.astimezone(utc).strftime("%Y-%m-%d %H:%M")
