from agent import send_invitations

test_booking = {"attendee_ids": [1, 2, 3]}

print(send_invitations(test_booking, simulate_failure=True))