
from datetime import datetime, timedelta

import pandas as pd

from sample_data import (
    get_employees,
    get_calendar_events,
    get_rooms,
    get_room_bookings
)

def _minutes(time_text):
    parsed = datetime.strptime(str(time_text), "%H:%M")
    return parsed.hour * 60 + parsed.minute

def _time_text(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

def _overlaps(start_a, end_a, start_b, end_b):
    # Back-to-back meetings are allowed.
    return start_a < end_b and start_b < end_a

def find_available_slots(
    meeting_date,
    attendee_ids,
    duration_minutes,
    work_start,
    work_end,
    preferred_start=None,
    preferred_end=None
):
    employees = get_employees()
    events = get_calendar_events()
    rooms = get_rooms()
    bookings = get_room_bookings()

    if not attendee_ids:
        return []

    if isinstance(meeting_date, str):
        meeting_date = datetime.strptime(
            meeting_date, "%Y-%m-%d"
        ).date()

    day_text = meeting_date.isoformat()

    work_start_min = _minutes(work_start)
    work_end_min = _minutes(work_end)

    search_start_min = (
        _minutes(preferred_start)
        if preferred_start else work_start_min
    )

    search_end_min = (
        _minutes(preferred_end)
        if preferred_end else work_end_min
    )

    # The preferred window must remain within work boundaries.
    search_start_min = max(search_start_min, work_start_min)
    search_end_min = min(search_end_min, work_end_min)

    if search_end_min <= search_start_min:
        return []

    if duration_minutes <= 0:
        return []

    selected_employees = employees[
        employees["employee_id"].isin(attendee_ids)
    ]

    if len(selected_employees) != len(set(attendee_ids)):
        return []

    attendee_count = len(set(attendee_ids))

    day_events = events[events["date"] == day_text]
    day_bookings = bookings[bookings["date"] == day_text]

    results = []

    # Check every possible 15-minute start time inside the window.
    for start_min in range(
        search_start_min,
        search_end_min - duration_minutes + 1,
        15
    ):
        end_min = start_min + duration_minutes

        if end_min > search_end_min:
            continue

        all_attendees_free = True

        for employee_id in attendee_ids:
            employee_events = day_events[
                day_events["employee_id"] == employee_id
            ]

            for _, event in employee_events.iterrows():
                event_start = _minutes(event["start"])
                event_end = _minutes(event["end"])

                if _overlaps(
                    start_min, end_min, event_start, event_end
                ):
                    all_attendees_free = False
                    break

            if not all_attendees_free:
                break

        if not all_attendees_free:
            continue

        for _, room in rooms.iterrows():
            if int(room["capacity"]) < attendee_count:
                continue

            room_id = int(room["room_id"])
            room_bookings = day_bookings[
                day_bookings["room_id"] == room_id
            ]

            room_free = True

            for _, booking in room_bookings.iterrows():
                booking_start = _minutes(booking["start"])
                booking_end = _minutes(booking["end"])

                if _overlaps(
                    start_min, end_min,
                    booking_start, booking_end
                ):
                    room_free = False
                    break

            if room_free:
                results.append({
                    "date": day_text,
                    "start": _time_text(start_min),
                    "end": _time_text(end_min),
                    "room_id": room_id,
                    "room_name": room["room_name"],
                    "capacity": int(room["capacity"]),
                    "attendee_count": attendee_count,
                    "duration_minutes": duration_minutes
                })

    return results

def get_booking_history(start_date, end_date):
    bookings = get_room_bookings()
    rooms = get_rooms()

    if isinstance(start_date, str):
        start_date = datetime.strptime(
            start_date, "%Y-%m-%d"
        ).date()

    if isinstance(end_date, str):
        end_date = datetime.strptime(
            end_date, "%Y-%m-%d"
        ).date()

    if end_date < start_date:
        return pd.DataFrame()

    bookings["date"] = pd.to_datetime(bookings["date"]).dt.date

    filtered = bookings[
        (bookings["date"] >= start_date)
        & (bookings["date"] <= end_date)
    ].copy()

    filtered = filtered.merge(
        rooms[["room_id", "room_name", "capacity", "location"]],
        on="room_id",
        how="left"
    )

    return filtered.sort_values(
        ["date", "start", "room_id"]
    ).reset_index(drop=True)