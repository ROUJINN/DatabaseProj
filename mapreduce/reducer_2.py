#!/usr/bin/env python3
import sys

current_user = None
op_counts = {}
total_count = 0

# Note: Input must be sorted by key (username)
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    user, op = line.split("\t")

    if current_user == user:
        op_counts[op] = op_counts.get(op, 0) + 1
        total_count += 1
    else:
        if current_user:
            # Output format: TotalCount \t Username \t OpDetails
            ops_str = ", ".join([f"{k}:{v}" for k, v in op_counts.items()])
            print(f"{total_count}\t{current_user}\t{ops_str}")

        current_user = user
        op_counts = {op: 1}
        total_count = 1

if current_user:
    ops_str = ", ".join([f"{k}:{v}" for k, v in op_counts.items()])
    print(f"{total_count}\t{current_user}\t{ops_str}")
