import streamlit as st
import pandas as pd
import calendar
import html

from datetime import date

from sample_data import (
    get_employees,
    get_rooms,
    get_room_bookings,
)

from scheduler import (
    find_available_slots,
    get_booking_history,
)

from agent import (
    understand_request,
    run_agent,
    load_bookings,
)


# --------------------------------------------------
# 1. PAGE SETUP
# --------------------------------------------------

st.set_page_config(
    page_title="Meet Match AI",
    page_icon="📅",
    layout="wide",
)

TODAY = date.today()
YEAR_END = date(2026, 12, 31)
YEAR_START = date(2026, 1, 1)

st.title("Meet Match AI")
st.subheader("AI-Powered Meeting Slot & Room Finder")

st.write(
    "Describe your meeting in natural language, "
    "find suitable available slots, and confirm a booking "
    "only after reviewing the details."
)

st.caption(
    "Gemini request understanding • Calendar conflict checking "
    "• Room availability • Human approval"
)

st.divider()


# --------------------------------------------------
# 2. LOAD DATA
# --------------------------------------------------

employees = get_employees()
rooms = get_rooms()

employee_names = employees["name"].tolist()
default_attendees = employee_names[:3]

# Prepare safe defaults from the latest Gemini extraction.
# A changing form version resets the widgets when a new AI request is processed.
ai_details = st.session_state.get("ai_meeting_details", {})
ai_form_version = st.session_state.get("ai_form_version", 0)

ai_date = TODAY
try:
    raw_ai_date = ai_details.get("meeting_date")
    if raw_ai_date:
        parsed_ai_date = date.fromisoformat(str(raw_ai_date))
        if TODAY <= parsed_ai_date <= YEAR_END:
            ai_date = parsed_ai_date
except (ValueError, TypeError):
    pass

try:
    ai_duration = int(ai_details.get("duration_minutes") or 45)
except (ValueError, TypeError):
    ai_duration = 45
if ai_duration <= 0:
    ai_duration = 45

ai_start = str(ai_details.get("preferred_start") or "11:00")
ai_end = str(ai_details.get("preferred_end") or "12:00")

raw_ai_attendees = ai_details.get("attendee_names") or []
if isinstance(raw_ai_attendees, str):
    raw_ai_attendees = [raw_ai_attendees]
if not isinstance(raw_ai_attendees, (list, tuple)):
    raw_ai_attendees = []

matched_attendees = []
for requested_name in raw_ai_attendees:
    requested = str(requested_name).strip().lower()
    if not requested:
        continue
    matches = [
        name for name in employee_names
        if requested == str(name).strip().lower()
        or requested in str(name).strip().lower()
        or str(name).strip().lower() in requested
    ]
    for matched_name in matches:
        if matched_name not in matched_attendees:
            matched_attendees.append(matched_name)


# --------------------------------------------------
# 3. GEMINI MEETING REQUEST
# --------------------------------------------------

st.header("1. AI Meeting Assistant")

st.write(
    "Describe the meeting you want. Gemini will extract "
    "the requested details for you to review."
)

with st.form("ai_request_form"):

    user_request = st.text_input(
        "Describe your meeting",
        placeholder=(
            "Schedule a 45-minute design meeting "
            "tomorrow afternoon with Alice and Bob"
        ),
    )

    ai_request_clicked = st.form_submit_button(
        "Understand Request with Gemini",
        type="primary",
    )


if ai_request_clicked:

    if not user_request.strip():
        st.warning("Please describe the meeting first.")

    else:

        with st.spinner("Gemini is understanding your request..."):

            try:
                details = understand_request(user_request)

                st.session_state["ai_meeting_details"] = details
                st.session_state["ai_original_request"] = user_request
                st.session_state["ai_form_version"] = (
                    st.session_state.get("ai_form_version", 0) + 1
                )

                st.success("Gemini extracted the meeting details.")

            except Exception as error:
                st.error(
                    "Gemini could not process the request. "
                    "Check your connection and API settings."
                )
                st.caption(str(error))


if "ai_meeting_details" in st.session_state:

    st.subheader("Extracted Meeting Details")

    st.json(st.session_state["ai_meeting_details"])

    st.info(
        "These are AI-extracted details, not a booking. "
        "Review them and use the scheduling form below "
        "to select actual attendees and a date."
    )


st.divider()


# --------------------------------------------------
# 4. NEW MEETING SEARCH
# --------------------------------------------------

st.header("2. Find an Available Meeting Slot")

st.write(
    "Choose the date, attendees, duration and allowed time window."
)

with st.form("meeting_search_form"):

    meeting_date = st.date_input(
        "Meeting date",
        value=ai_date,
        min_value=TODAY,
        max_value=YEAR_END,
        key=f"meeting_date_ai_{ai_form_version}",
    )

    col1, col2 = st.columns(2)

    with col1:

        attendee_names = st.multiselect(
            "Select attendees",
            options=employee_names,
            default=matched_attendees if matched_attendees else default_attendees,
            key=f"attendee_names_ai_{ai_form_version}",
        )

        duration_options = sorted(set([30, 45, 60, 90, ai_duration]))
        duration = st.selectbox(
            "Meeting duration (minutes)",
            options=duration_options,
            index=duration_options.index(ai_duration),
            key=f"duration_ai_{ai_form_version}",
        )

        earliest_start = st.selectbox(
            "Earliest allowed meeting start",
            options=[
                "09:00", "09:30", "10:00", "10:30",
                "11:00", "12:00",
            ],
            index=0,
        )

        latest_end = st.selectbox(
            "Latest allowed meeting end",
            options=[
                "12:00", "13:00", "14:00", "15:00",
                "16:00", "17:00",
            ],
            index=5,
        )

    with col2:

        preferred_start = st.selectbox(
            "Preferred meeting window — start",
            options=[
                "09:00", "09:15", "09:30", "09:45",
                "10:00", "10:15", "10:30", "10:45",
                "11:00", "11:15", "11:30", "11:45",
                "12:00", "12:15", "12:30", "12:45",
                "13:00", "13:15", "13:30", "13:45",
                "14:00", "14:15", "14:30", "14:45",
                "15:00", "15:15", "15:30", "15:45",
                "16:00",
            ],
            index=(
                [
                    "09:00", "09:15", "09:30", "09:45",
                    "10:00", "10:15", "10:30", "10:45",
                    "11:00", "11:15", "11:30", "11:45",
                    "12:00", "12:15", "12:30", "12:45",
                    "13:00", "13:15", "13:30", "13:45",
                    "14:00", "14:15", "14:30", "14:45",
                    "15:00", "15:15", "15:30", "15:45",
                    "16:00",
                ].index(ai_start)
                if ai_start in [
                    "09:00", "09:15", "09:30", "09:45",
                    "10:00", "10:15", "10:30", "10:45",
                    "11:00", "11:15", "11:30", "11:45",
                    "12:00", "12:15", "12:30", "12:45",
                    "13:00", "13:15", "13:30", "13:45",
                    "14:00", "14:15", "14:30", "14:45",
                    "15:00", "15:15", "15:30", "15:45",
                    "16:00",
                ] else 8
            ),
            key=f"preferred_start_ai_{ai_form_version}",
        )

        preferred_end = st.selectbox(
            "Preferred meeting window — end",
            options=[
                "09:30", "09:45", "10:00", "10:15",
                "10:30", "10:45", "11:00", "11:15",
                "11:30", "11:45", "12:00", "12:15",
                "12:30", "12:45", "13:00", "13:15",
                "13:30", "13:45", "14:00", "14:15",
                "14:30", "14:45", "15:00", "15:15",
                "15:30", "15:45", "16:00", "16:15",
                "16:30", "16:45", "17:00",
            ],
            index=(
                [
                    "09:30", "09:45", "10:00", "10:15",
                    "10:30", "10:45", "11:00", "11:15",
                    "11:30", "11:45", "12:00", "12:15",
                    "12:30", "12:45", "13:00", "13:15",
                    "13:30", "13:45", "14:00", "14:15",
                    "14:30", "14:45", "15:00", "15:15",
                    "15:30", "15:45", "16:00", "16:15",
                    "16:30", "16:45", "17:00",
                ].index(ai_end)
                if ai_end in [
                    "09:30", "09:45", "10:00", "10:15",
                    "10:30", "10:45", "11:00", "11:15",
                    "11:30", "11:45", "12:00", "12:15",
                    "12:30", "12:45", "13:00", "13:15",
                    "13:30", "13:45", "14:00", "14:15",
                    "14:30", "14:45", "15:00", "15:15",
                    "15:30", "15:45", "16:00", "16:15",
                    "16:30", "16:45", "17:00",
                ] else 9
            ),
            key=f"preferred_end_ai_{ai_form_version}",
        )

    search_clicked = st.form_submit_button(
        "Find Available Slots",
        type="primary",
    )


# --------------------------------------------------
# 5. PROCESS THE SEARCH
# --------------------------------------------------

if search_clicked:

    if not attendee_names:

        st.error("Select at least one attendee.")

    elif preferred_end <= preferred_start:

        st.error(
            "The preferred window end must be later than its start."
        )

    elif preferred_start < earliest_start:

        st.error(
            "The preferred start must be at or after "
            "the earliest allowed start."
        )

    elif preferred_end > latest_end:

        st.error(
            "The preferred end must be at or before "
            "the latest allowed meeting end."
        )

    else:

        attendee_ids = employees[
            employees["name"].isin(attendee_names)
        ]["employee_id"].tolist()

        with st.spinner("Checking calendars and rooms..."):

            try:

                slots = find_available_slots(
                    meeting_date=meeting_date,
                    attendee_ids=attendee_ids,
                    duration_minutes=duration,
                    work_start=earliest_start,
                    work_end=latest_end,
                    preferred_start=preferred_start,
                    preferred_end=preferred_end,
                )

                st.session_state["meeting_slots"] = slots
                st.session_state["meeting_date"] = str(meeting_date)
                st.session_state["attendee_names"] = attendee_names
                st.session_state["attendee_ids"] = attendee_ids
                st.session_state["duration"] = duration

                st.session_state.pop("selected_slot", None)
                st.session_state.pop("last_booking_result", None)

            except Exception as error:

                st.error(f"Search failed: {error}")


# --------------------------------------------------
# 6. SHOW AVAILABLE RESULTS
# --------------------------------------------------

if "meeting_slots" in st.session_state:

    slots = st.session_state["meeting_slots"]

    st.divider()
    st.header("3. Recommended Meeting Slots")

    if not slots:

        st.warning(
            "No suitable slots were found. Try another date, "
            "time window or set of attendees."
        )

    else:

        st.success(
            f"Found {len(slots)} available slot-room combinations."
        )

        for index, slot in enumerate(slots):

            with st.container(border=True):

                left, right = st.columns([3, 1])

                with left:

                    st.subheader(
                        f"{slot['start']} – {slot['end']}"
                    )

                    st.write(f"**Date:** {slot['date']}")
                    st.write(f"**Room:** {slot['room_name']}")

                    st.write(
                        "**Attendees:** "
                        + ", ".join(
                            st.session_state["attendee_names"]
                        )
                    )

                with right:

                    st.metric(
                        "Room capacity",
                        slot["capacity"],
                    )

                    st.write(
                        f"Duration: {slot['duration_minutes']} minutes"
                    )

                if st.button(
                    "Select This Slot",
                    key=f"select_{index}",
                ):

                    st.session_state["selected_slot"] = slot

                    st.session_state["selected_slot_signature"] = (
                        str(slot["date"]),
                        slot["start"],
                        slot["end"],
                        int(slot["room_id"]),
                    )

                    st.session_state.pop("last_booking_result", None)


# --------------------------------------------------
# 7. REVIEW AND APPROVE BOOKING
# --------------------------------------------------

if "selected_slot" in st.session_state:

    selected = st.session_state["selected_slot"]

    st.divider()
    st.header("4. Review and Confirm Meeting")

    st.write(f"**Date:** {selected['date']}")

    st.write(
        f"**Time:** {selected['start']} – {selected['end']}"
    )

    st.write(f"**Room:** {selected['room_name']}")
    st.write(f"**Capacity:** {selected['capacity']}")

    st.write(
        "**Attendees:** "
        + ", ".join(st.session_state["attendee_names"])
    )

    st.warning(
        "Nothing is booked yet. Review the details and approve "
        "the booking below."
    )

    approved = st.checkbox(
        "I have reviewed these details and approve this booking.",
        key="approve_meeting_booking",
    )

    if st.button(
        "Confirm Booking",
        type="primary",
        key="confirm_meeting_booking",
    ):

        if not approved:

            st.warning(
                "Please check the approval box before booking."
            )

        else:

            with st.spinner("Rechecking availability and saving booking..."):

                try:

                    result = run_agent(
                        slot=selected,
                        attendee_ids=st.session_state["attendee_ids"],
                        approved=True,
                    )

                    st.session_state["last_booking_result"] = result

                    if result["booking_success"]:

                        st.success(result["message"])

                        st.json(result["booking"])

                    else:

                        st.error(result["message"])

                except Exception as error:

                    st.error(
                        "The booking process encountered an error. "
                        "Check the error details before trying again."
                    )

                    st.caption(str(error))


# --------------------------------------------------
# 8. SHOW LAST BOOKING RESULT
# --------------------------------------------------

if "last_booking_result" in st.session_state:

    result = st.session_state["last_booking_result"]

    if result.get("booking_success"):

        st.success("Booking status: CONFIRMED")

        st.write(result["message"])

    else:

        st.warning("Booking status: NOT CONFIRMED")

        st.write(result["message"])


# --------------------------------------------------
# 9. CALENDAR BOOKING HISTORY
# --------------------------------------------------

st.divider()
st.header("5. Meeting Calendar")
st.write(
    "Browse the 2026 calendar. Blue event labels include existing sample "
    "meetings and newly confirmed bookings saved by Meet Match AI."
)

# Load the original sample history and locally confirmed bookings together.
try:
    sample_history = get_booking_history(YEAR_START, YEAR_END)
    if isinstance(sample_history, pd.DataFrame):
        sample_records = sample_history.to_dict(orient="records")
    else:
        sample_records = list(sample_history or [])
except Exception as error:
    sample_records = []
    st.warning(f"Could not load sample booking history: {error}")

try:
    local_records = load_bookings()
except Exception as error:
    local_records = []
    st.error(f"Could not load locally saved bookings: {error}")

events = []
for record in sample_records:
    item = dict(record)
    # Do not imply that future months are already booked using generated demo data.
    # Locally confirmed bookings are still shown for any month.
    try:
        sample_date = pd.to_datetime(item.get("date"), errors="coerce").date()
    except (TypeError, ValueError, AttributeError):
        sample_date = None
    if sample_date and sample_date.year == 2026 and sample_date.month > TODAY.month:
        continue
    item["source"] = "Existing sample booking"
    item["status"] = item.get("status", "existing")
    events.append(item)
for record in local_records:
    item = dict(record)
    item["source"] = "New local booking"
    item["status"] = item.get("status", "confirmed")
    events.append(item)

history = pd.DataFrame(events)
if history.empty:
    history = pd.DataFrame(columns=[
        "booking_id", "date", "start", "end", "room_name", "status", "source"
    ])
else:
    if "date" not in history.columns:
        history["date"] = None
    history["date"] = pd.to_datetime(history["date"], errors="coerce").dt.date
    history = history[
        history["date"].notna()
        & (history["date"] >= YEAR_START)
        & (history["date"] <= YEAR_END)
    ].copy()
    for column, default in [
        ("booking_id", ""), ("start", "Time not specified"), ("end", ""),
        ("room_name", "Room not specified"), ("status", "existing"),
        ("source", "Existing sample booking"),
    ]:
        if column not in history.columns:
            history[column] = default
    history["start"] = history["start"].fillna("Time not specified").astype(str)
    history["end"] = history["end"].fillna("").astype(str)
    history["room_name"] = history["room_name"].fillna("Room not specified").astype(str)

if "calendar_month" not in st.session_state:
    st.session_state["calendar_month"] = date(2026, max(1, min(12, TODAY.month)), 1)

month_date = st.session_state["calendar_month"]
nav1, nav2, nav3 = st.columns([1, 1, 5])
with nav1:
    if st.button("← Previous", disabled=month_date.month <= 1, key="calendar_prev"):
        st.session_state["calendar_month"] = date(2026, month_date.month - 1, 1)
        st.rerun()
with nav2:
    if st.button("Today", key="calendar_today"):
        st.session_state["calendar_month"] = date(2026, max(1, min(12, TODAY.month)), 1)
        st.rerun()
with nav3:
    st.subheader(month_date.strftime("%B %Y"))
with st.container():
    if st.button("Next →", disabled=month_date.month >= 12, key="calendar_next"):
        st.session_state["calendar_month"] = date(2026, month_date.month + 1, 1)
        st.rerun()

# Draw a clickable month grid. Clicking any date selects it and displays ALL
# meetings for that date in the details section below.
weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(2026, month_date.month)
header_cols = st.columns(7)
for col, weekday in zip(header_cols, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
    col.markdown(f"<div style='text-align:center;background:#eaf2ff;color:#1554b8;padding:8px;border-radius:6px;font-weight:700'>{weekday}</div>", unsafe_allow_html=True)

if "inspect_history_date" not in st.session_state:
    st.session_state["inspect_history_date"] = date(
        2026, month_date.month,
        min(TODAY.day, calendar.monthrange(2026, month_date.month)[1]),
    )

for week_index, week in enumerate(weeks):
    day_cols = st.columns(7)
    for col, day in zip(day_cols, week):
        with col:
            is_current_month = day.month == month_date.month
            day_events = history[history["date"] == day] if not history.empty else pd.DataFrame()
            if not is_current_month:
                st.markdown(f"<div style='color:#aab2bf;text-align:center;padding:6px'>{day.day}</div>", unsafe_allow_html=True)
            else:
                if day == TODAY:
                    button_label = f"🔵 {day.day} · Today"
                elif not day_events.empty:
                    button_label = f"🔵 {day.day} · {len(day_events)}"
                else:
                    button_label = str(day.day)
                if st.button(
                    button_label,
                    key=f"calendar_day_{day.isoformat()}",
                    use_container_width=True,
                    type="primary" if st.session_state.get("inspect_history_date") == day else "secondary",
                ):
                    st.session_state["inspect_history_date"] = day
                    st.rerun()
                # Show a compact preview; selecting the date reveals every event below.
                if not day_events.empty:
                    day_events = day_events.sort_values(by="start", kind="stable")
                    for _, event in day_events.head(2).iterrows():
                        label = html.escape(f"{event.get('start', '')} {event.get('room_name', 'Meeting')}")
                        st.markdown(
                            f"<div style='background:#dbeafe;color:#164eaa;border-left:3px solid #2563eb;border-radius:4px;padding:3px 4px;margin:2px 0;font-size:10px;overflow-wrap:anywhere'>{label}</div>",
                            unsafe_allow_html=True,
                        )
                    if len(day_events) > 2:
                        st.caption(f"+{len(day_events) - 2} more")
            st.markdown("<div style='height:5px;border-bottom:1px solid #e2e8f0;margin-bottom:5px'></div>", unsafe_allow_html=True)

st.caption(
    f"Showing {len(history):,} bookings in 2026, including "
    f"{len(local_records):,} locally saved booking(s). Generated sample bookings are hidden in future months; actual local bookings remain visible."
)

# The selected date is controlled by clicking any date in the calendar.
selected_history_date = st.session_state["inspect_history_date"]
st.subheader(f"Meetings on {selected_history_date.strftime('%d %B %Y')}")
selected_events = history[history["date"] == selected_history_date] if not history.empty else pd.DataFrame()
if selected_events.empty:
    st.info("No meetings are listed for this date.")
else:
    for _, event in selected_events.sort_values(by="start", kind="stable").iterrows():
        with st.container(border=True):
            st.markdown(f"**🔵 {event['start']} – {event['end']} · {event['room_name']}**")
            st.caption(f"Status: {event['status']} · Source: {event['source']}")
            if event.get("booking_id"):
                st.caption(f"Booking ID: {event['booking_id']}")
            attendee_ids = event.get("attendee_ids", [])
            if isinstance(attendee_ids, (list, tuple)) and attendee_ids:
                st.write("Attendee IDs: " + ", ".join(map(str, attendee_ids)))

if not history.empty:
    csv_history = history.copy()
    csv_history["date"] = csv_history["date"].astype(str)
    st.download_button(
        "Download Booking History as CSV",
        data=csv_history.to_csv(index=False).encode("utf-8"),
        file_name="meet_match_ai_booking_history.csv",
        mime="text/csv",
    )


# --------------------------------------------------
# 10. DATASET SUMMARY
# --------------------------------------------------

st.divider()
st.header("6. Dataset Summary")

summary1, summary2, summary3 = st.columns(3)

summary1.metric("Employees", len(employees))
summary2.metric("Meeting rooms", len(rooms))
summary3.metric(
    "Simulated bookings",
    len(get_room_bookings()),
)

st.caption(
    "Meet Match AI | Hackathon prototype | "
    "Synthetic data, not a live company calendar"
)