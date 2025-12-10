import sys
from collections import defaultdict

# Since we are simulating or running in a mode where we want to find the top 10 globally,
# and standard reducers process key by key, we have a challenge.
# In a real distributed setting, we'd need a second job to sort by count.
# However, for this assignment, we can assume a single reducer that sees all data (sorted by user),
# or we can accumulate everything in memory if the dataset is small enough.
# Given the context, we'll accumulate per-user stats and then sort at the end.

user_stats = defaultdict(lambda: defaultdict(int))

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    parts = line.split("\t")
    if len(parts) < 2:
        continue

    username, op = parts
    user_stats[username][op] += 1

# Calculate total per user and prepare for sorting
# List of (username, total_count, op_counts_dict)
results = []
for username, ops in user_stats.items():
    total = sum(ops.values())
    results.append((username, total, ops))

# Sort by total count descending
results.sort(key=lambda x: x[1], reverse=True)

# Output top 10
print("Top 10 Users by Total Operation Count:")
print(f"{'Rank':<5} {'Username':<20} {'Total':<10} {'Details'}")
print("-" * 60)

for i, (username, total, ops) in enumerate(results[:10], 1):
    details = ", ".join([f"{k}: {v}" for k, v in ops.items()])
    print(f"{i:<5} {username:<20} {total:<10} {details}")
