from scheduler import find_available_slots


def test_free_slots_exist():
    slots = find_available_slots(
        meeting_date="2026-10-20",
        attendee_ids=[1],
        duration_minutes=30,
        work_start="09:00",
        work_end="17:00"
    )

    assert len(slots) > 0, "No available meeting slots were found!"
    print("PASS: Available meeting slots were found.")


def test_room_is_provided():
    slots = find_available_slots(
        meeting_date="2026-10-20",
        attendee_ids=[1],
        duration_minutes=30,
        work_start="09:00",
        work_end="17:00"
    )

    assert all(slot["room_name"] for slot in slots)
    print("PASS: Every suggested slot has a room.")


def test_room_capacity():
    slots = find_available_slots(
        meeting_date="2026-10-20",
        attendee_ids=[1],
        duration_minutes=30,
        work_start="09:00",
        work_end="17:00"
    )

    assert all(slot["capacity"] >= slot["attendee_count"] for slot in slots)
    print("PASS: Room capacity is sufficient.")


if __name__ == "__main__":
    test_free_slots_exist()
    test_room_is_provided()
    test_room_capacity()
    print("\nAll basic scheduling tests completed!")