#!/usr/bin/env python3
import sys

# Date Range: 2025/12/14 to 2025/12/21
START_DATE = "2025/12/14"
END_DATE = "2025/12/21"

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    parts = line.split("\t")
    if len(parts) != 4:
        continue

    date_str, time_str, username, op = parts

    if START_DATE <= date_str <= END_DATE:
        print(f"{op}\t1")
