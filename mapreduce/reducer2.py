import sys
from collections import defaultdict

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
