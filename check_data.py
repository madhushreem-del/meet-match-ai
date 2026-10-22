from sample_data import (
    get_employees,
    get_calendar_events,
    get_rooms,
    get_room_bookings
)

employees = get_employees()
events = get_calendar_events()
rooms = get_rooms()
bookings = get_room_bookings()

print("\nDATASET SUMMARY")
print("-------------------------")

print("Employees:", len(employees))
print("Calendar events:", len(events))
print("Meeting rooms:", len(rooms))
print("Room bookings:", len(bookings))

print("\nEMPLOYEE SAMPLE")
print(employees.head())

print("\nCALENDAR EVENT SAMPLE")
print(events.head())

print("\nROOM SAMPLE")
print(rooms.head())

print("\nROOM BOOKING SAMPLE")
print(bookings.head())