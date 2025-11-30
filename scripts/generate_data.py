import datetime
import random
import sys

try:
    from faker import Faker
except ImportError:
    print("Faker not installed. Please run 'pip install faker'")
    sys.exit(1)

fake = Faker("zh_CN")

# Configuration
NUM_STUDENTS = 30
NUM_FACULTY = 10
START_DATE = datetime.date(2025, 12, 14)
END_DATE = datetime.date(2025, 12, 28)
DEPARTMENTS = ["智能学院", "计算机学院", "数学学院", "物理学院"]
MERCHANTS = ["农园", "学五", "物美超市", "文印店"]
BUILDINGS = [
    ("宿舍A栋", "北门"),
    ("理科二号楼", "西门"),
    ("图书馆", "东门"),
    ("体育馆", "南门"),
]

sql_statements = []
sql_statements.append("USE smart_campus;")
sql_statements.append("SET NAMES utf8mb4;")

# 1. Access Points
points = []
for i, (b, gate) in enumerate(BUILDINGS):
    pid = i + 1
    dept = random.choice(DEPARTMENTS)
    sql_statements.append(
        f"INSERT INTO AccessPoints (point_id, building_name, manager_dept_id) VALUES ({pid}, '{b} ({gate})', '{dept}');"
    )
    points.append(pid)

# 2. Users & Cards
users = []
cards = []

# Admin
sql_statements.append(
    "INSERT INTO Users (user_id, username, password, role) VALUES (1, 'admin', 'admin123', 'admin');"
)

user_id_counter = 2

# Students
students = []
# Ensure "王X明" exists
wang_ming_name = "王小明"
wang_ming_exists = False

for i in range(NUM_STUDENTS):
    uid = user_id_counter
    user_id_counter += 1

    if not wang_ming_exists:
        name = wang_ming_name
        wang_ming_exists = True
        dept = "智能学院"  # Assign to target dept for queries
    else:
        name = fake.name()
        dept = random.choice(DEPARTMENTS)

    username = f"stu{i}"
    sid = f"2022{i:04d}"

    sql_statements.append(
        f"INSERT INTO Users (user_id, username, password, role) VALUES ({uid}, '{username}', '123456', 'student');"
    )
    sql_statements.append(
        f"INSERT INTO Students (student_id, user_id, name, gender, phone, email, department, grade) VALUES ('{sid}', {uid}, '{name}', '{random.choice(['M', 'F'])}', '{fake.phone_number()}', '{fake.email()}', '{dept}', '2022');"
    )

    # Card
    cid = f"CARD{sid}"
    balance = random.uniform(100, 1000)
    sql_statements.append(
        f"INSERT INTO Cards (card_id, user_id, status, balance, subsidy_balance, open_date) VALUES ('{cid}', {uid}, 'normal', {balance:.2f}, 0, '2022-09-01');"
    )

    students.append({"uid": uid, "sid": sid, "cid": cid, "dept": dept, "name": name})

# Faculty
faculty = []
for i in range(NUM_FACULTY):
    uid = user_id_counter
    user_id_counter += 1

    name = fake.name()
    dept = random.choice(DEPARTMENTS)
    username = f"fac{i}"
    fid = f"F{i:04d}"

    sql_statements.append(
        f"INSERT INTO Users (user_id, username, password, role) VALUES ({uid}, '{username}', '123456', 'faculty');"
    )
    sql_statements.append(
        f"INSERT INTO Faculty (staff_id, user_id, name, identity_card, phone, email, department) VALUES ('{fid}', {uid}, '{name}', '{fake.ssn()}', '{fake.phone_number()}', '{fake.email()}', '{dept}');"
    )

    # Card
    cid = f"CARD{fid}"
    balance = random.uniform(500, 2000)
    sql_statements.append(
        f"INSERT INTO Cards (card_id, user_id, status, balance, subsidy_balance, open_date) VALUES ('{cid}', {uid}, 'normal', {balance:.2f}, 0, '2020-09-01');"
    )

    faculty.append({"uid": uid, "fid": fid, "cid": cid, "dept": dept})

all_people = students + faculty

# 3. Transactions & Logs
current_date = START_DATE
delta = datetime.timedelta(days=1)

while current_date <= END_DATE:
    for person in all_people:
        # Random Transactions
        if random.random() < 0.7:  # 70% chance of transaction
            for _ in range(random.randint(1, 3)):
                amount = random.uniform(5, 50)
                merchant = random.choice(MERCHANTS)
                # Time: 07:00 to 22:00
                hour = random.randint(7, 21)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                dt = datetime.datetime.combine(
                    current_date, datetime.time(hour, minute, second)
                )

                sql_statements.append(
                    f"INSERT INTO Transactions (card_id, trans_type, amount, merchant_name, time) VALUES ('{person['cid']}', 'payment', {amount:.2f}, '{merchant}', '{dt}');"
                )

        # Random Access Logs
        if random.random() < 0.6:
            for _ in range(random.randint(1, 2)):
                pid = random.choice(points)
                direction = random.choice(["in", "out"])
                # Time: 06:00 to 23:00
                hour = random.randint(6, 23)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                dt = datetime.datetime.combine(
                    current_date, datetime.time(hour, minute, second)
                )

                sql_statements.append(
                    f"INSERT INTO AccessLogs (card_id, point_id, direction, time) VALUES ('{person['cid']}', {pid}, '{direction}', '{dt}');"
                )

    current_date += delta

# 4. Inject Specific Data for Queries

# Query 7: "计算机学院" student night access (22:00-06:00) at Science 2 (pid=2 usually)
# Find a CS student
cs_students = [s for s in students if s["dept"] == "计算机学院"]
if not cs_students:
    # Force one
    students[1]["dept"] = "计算机学院"
    sql_statements.append(
        f"UPDATE Students SET department='计算机学院' WHERE student_id='{students[1]['sid']}';"
    )
    cs_students = [students[1]]

target_cs_stu = cs_students[0]
# Add night access
night_time = datetime.datetime(2025, 12, 20, 23, 30, 0)
sql_statements.append(
    f"INSERT INTO AccessLogs (card_id, point_id, direction, time) VALUES ('{target_cs_stu['cid']}', 2, 'in', '{night_time}');"
)

# Query 5: "智能学院" student max daily avg consumption merchant (2025-12-14 to 19)
# Ensure some data there. The random generation should cover it, but let's add a big one.
ai_students = [s for s in students if s["dept"] == "智能学院"]
if ai_students:
    target_ai_stu = ai_students[0]
    # Add big consumption at '文印店'
    dt = datetime.datetime(2025, 12, 15, 12, 0, 0)
    sql_statements.append(
        f"INSERT INTO Transactions (card_id, trans_type, amount, merchant_name, time) VALUES ('{target_ai_stu['cid']}', 'payment', 100.00, '文印店', '{dt}');"
    )

# Write to file
with open("sql/data.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(sql_statements))

print("Data generation complete. Check sql/data.sql")
