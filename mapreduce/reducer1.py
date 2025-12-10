import sys

current_op = None
current_count = 0

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    op, count = line.split("\t")
    try:
        count = int(count)
    except ValueError:
        continue

    if current_op == op:
        current_count += count
    else:
        if current_op:
            print(f"{current_op}\t{current_count}")
        current_op = op
        current_count = count

if current_op:
    print(f"{current_op}\t{current_count}")
