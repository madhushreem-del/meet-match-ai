
import random
from datetime import date, datetime, timedelta

import pandas as pd

YEAR_START = date(2026, 1, 1)
YEAR_END = date(2026, 12, 31)

EMPLOYEE_COUNT = 150
ROOM_COUNT = 20
ROOM_BOOKING_COUNT = 1906

FIRST_NAMES = [
    "Aarav", "Akash", "Aditya", "Arjun", "Ananya",
    "Aditi", "Diya", "Priya", "Rohan", "Rahul",
    "Sneha", "Kavya", "Ishaan", "Meera", "Kiran",
    "Nisha", "Varun", "Pooja", "Vikram", "Neha",
    "Sanjay", "Sahana", "Riya", "Dev", "Ira",
    "Manish", "Tanvi", "Nikhil", "Anika", "Ayaan"
]

LAST_NAMES = [
    "Sharma", "Reddy", "Patel", "Kumar", "Shah",
    "Rao", "Nair", "Gupta", "Mehta", "Iyer",
    "Das", "Verma", "Joshi", "Singh", "Shetty"
]

DEPARTMENTS = [
    "Design", "Engineering", "Marketing",
    "Human Resources", "Finance", "Sales",
    "Operations", "Product", "Research",
    "Customer Support"
]

def get_employees():
    rng = random.Random(101)
    employees = []

    for i in range(1, EMPLOYEE_COUNT + 1):
        first = FIRST_NAMES[(i - 1) % len(FIRST_NAMES)]
        last = LAST_NAMES[((i - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)]

        employees.append({
            "employee_id": i,
            "name": f"{first} {last} {i:03d}",
            "department": DEPARTMENTS[(i - 1) % len(DEPARTMENTS)],
            "team": DEPARTMENTS[(i - 1) % len(DEPARTMENTS)],
            "timezone": (
                "Europe/London" if i == 3
                else "Asia/Kolkata"
            )
        })

    return pd.DataFrame(employees)

def get_rooms():
    room_types = [
        ("Meeting Room", 4),
        ("Collaboration Room", 8),
        ("Conference Room", 10),
        ("Board Room", 15),
        ("Innovation Room", 6)
    ]

    rooms = []

    for i in range(1, ROOM_COUNT + 1):
        room_type, capacity = room_types[(i - 1) % len(room_types)]

        rooms.append({
            "room_id": i,
            "room_name": f"{room_type} {i}",
            "capacity": capacity,
            "location": f"Floor {((i - 1) // 5) + 1}"
        })

    return pd.DataFrame(rooms)

def _business_dates():
    dates = []
    current = YEAR_START

    while current <= YEAR_END:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)

    return dates

def get_calendar_events():
    rng = random.Random(202)
    employees = get_employees()
    business_dates = _business_dates()
    events = []

    for _, employee in employees.iterrows():
        employee_id = int(employee["employee_id"])
        occupied = {}

        # Approximately 100 calendar events per employee per year.
        for _ in range(100):
            for attempt in range(100):
                day = rng.choice(business_dates)
                duration = rng.choice([30, 30, 45, 60, 60, 90])
                start_minute = rng.randrange(9 * 60, 16 * 60 + 1, 15)
                end_minute = start_minute + duration

                if end_minute > 17 * 60:
                    continue

                intervals = occupied.setdefault(day, [])

                if any(
                    start_minute < existing_end
                    and existing_start < end_minute
                    for existing_start, existing_end in intervals
                ):
                    continue

                intervals.append((start_minute, end_minute))

                events.append({
                    "event_id": len(events) + 1,
                    "employee_id": employee_id,
                    "date": day.isoformat(),
                    "start": f"{start_minute // 60:02d}:{start_minute % 60:02d}",
                    "end": f"{end_minute // 60:02d}:{end_minute % 60:02d}"
                })
                break

    return pd.DataFrame(
        events,
        columns=["event_id", "employee_id", "date", "start", "end"]
    )

def get_room_bookings():
    rng = random.Random(303)
    business_dates = _business_dates()
    bookings = []
    occupied = {}

    # Create exactly 1,906 simulated bookings without room overlaps.
    for _ in range(ROOM_BOOKING_COUNT):
        created = False

        for attempt in range(1000):
            room_id = rng.randint(1, ROOM_COUNT)
            day = rng.choice(business_dates)
            duration = rng.choice([30, 30, 45, 60, 60, 90])
            start_minute = rng.randrange(9 * 60, 16 * 60 + 1, 15)
            end_minute = start_minute + duration

            if end_minute > 17 * 60:
                continue

            key = (room_id, day)
            intervals = occupied.setdefault(key, [])

            if any(
                start_minute < existing_end
                and existing_start < end_minute
                for existing_start, existing_end in intervals
            ):
                continue

            intervals.append((start_minute, end_minute))

            bookings.append({
                "booking_id": len(bookings) + 1,
                "room_id": room_id,
                "date": day.isoformat(),
                "start": f"{start_minute // 60:02d}:{start_minute % 60:02d}",
                "end": f"{end_minute // 60:02d}:{end_minute % 60:02d}"
            })

            created = True
            break

        if not created:
            raise RuntimeError(
                "Could not generate all room bookings."
            )

    return pd.DataFrame(
        bookings,
        columns=["booking_id", "room_id", "date", "start", "end"]
    )

def export_datasets():
    datasets = {
        "employees.csv": get_employees(),
        "calendar_events.csv": get_calendar_events(),
        "rooms.csv": get_rooms(),
        "room_bookings.csv": get_room_bookings()
    }

    for filename, dataframe in datasets.items():
        dataframe.to_csv(filename, index=False)
        print(f"{filename}: {len(dataframe)} records")

if __name__ == "__main__":
    export_datasets()