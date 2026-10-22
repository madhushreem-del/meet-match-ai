from agent import convert_london_time_to_utc

# Winter: London uses GMT (UTC+0)
winter = convert_london_time_to_utc("2026-01-15", "15:00")
print("Winter:", winter)

# Summer: London uses BST (UTC+1)
summer = convert_london_time_to_utc("2026-07-15", "15:00")
print("Summer:", summer)

assert winter == "2026-01-15 15:00"
assert summer == "2026-07-15 14:00"

print("London DST test passed!")