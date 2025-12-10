import sys

# Date range
START_DATE = "2025/12/14"
END_DATE = "2025/12/21"


def is_in_range(date_str):
    return START_DATE <= date_str <= END_DATE


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    parts = line.split("\t")
    if len(parts) < 4:
        continue

    date_str, time_str, username, op = parts

    if is_in_range(date_str):
        # Task 2 asks for "each operation" (每种操作), so we include all
        print(f"{username}\t{op}")
