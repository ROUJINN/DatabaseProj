import csv
import datetime
import io

import pymysql
from flask import (
    Flask,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this for production

# Database Configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "123456",  # UPDATE THIS
    "database": "smart_campus",
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_db_connection():
    return pymysql.connect(**db_config)


@app.route("/")
def index():
    if "user_id" in session:
        if session["role"] == "student":
            return redirect(url_for("student_dashboard"))
        elif session["role"] == "faculty":
            return redirect(url_for("faculty_dashboard"))
        elif session["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM Users WHERE username = %s AND password = %s"
                cursor.execute(sql, (username, password))
                user = cursor.fetchone()

                if user:
                    session["user_id"] = user["user_id"]
                    session["username"] = user["username"]
                    session["role"] = user["role"]
                    return redirect(url_for("index"))
                else:
                    flash("Invalid username or password")
        finally:
            conn.close()

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]
        name = request.form["name"]
        id_num = request.form["id_num"]  # Student ID or Staff ID
        dept = request.form["dept"]

        # Optional fields
        phone = request.form.get("phone", "")
        email = request.form.get("email", "")
        gender = request.form.get("gender", "M")

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 1. Create User
                cursor.execute(
                    "INSERT INTO Users (username, password, role) VALUES (%s, %s, %s)",
                    (username, password, role),
                )
                user_id = cursor.lastrowid

                # 2. Create Role-specific entry
                if role == "student":
                    cursor.execute(
                        "INSERT INTO Students (student_id, user_id, name, gender, phone, email, department, grade) VALUES (%s, %s, %s, %s, %s, %s, %s, '2025')",
                        (id_num, user_id, name, gender, phone, email, dept),
                    )
                    card_id = f"CARD{id_num}"
                elif role == "faculty":
                    # For faculty, we need identity_card. Let's just use id_num for simplicity or ask for it.
                    # Assuming id_num is staff_id. We'll generate a fake identity_card for now or ask in form.
                    # To keep it simple, we'll use id_num as identity_card too if not provided.
                    cursor.execute(
                        "INSERT INTO Faculty (staff_id, user_id, name, identity_card, phone, email, department) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (id_num, user_id, name, id_num, phone, email, dept),
                    )
                    card_id = f"CARD{id_num}"
                else:
                    flash("Invalid role")
                    return redirect(url_for("register"))

                # 3. Create Card
                cursor.execute(
                    "INSERT INTO Cards (card_id, user_id, status, balance, open_date) VALUES (%s, %s, 'normal', 0.00, CURDATE())",
                    (card_id, user_id),
                )

            conn.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for("login"))
        except Exception as e:
            conn.rollback()
            flash(f"Registration failed: {str(e)}")
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- Student Routes ---
@app.route("/student")
def student_dashboard():
    if "role" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Basic Info
            cursor.execute(
                "SELECT * FROM Students WHERE user_id = %s", (session["user_id"],)
            )
            student = cursor.fetchone()

            # Card Info
            cursor.execute(
                "SELECT * FROM Cards WHERE user_id = %s", (session["user_id"],)
            )
            card = cursor.fetchone()

            # Recent Transactions
            cursor.execute(
                "SELECT * FROM Transactions WHERE card_id = %s ORDER BY time DESC LIMIT 10",
                (card["card_id"],),
            )
            transactions = cursor.fetchall()

            # Recent Access Logs
            cursor.execute(
                """
                SELECT al.*, ap.building_name 
                FROM AccessLogs al 
                JOIN AccessPoints ap ON al.point_id = ap.point_id 
                WHERE card_id = %s ORDER BY time DESC LIMIT 10
            """,
                (card["card_id"],),
            )
            logs = cursor.fetchall()

            return render_template(
                "student_dashboard.html",
                student=student,
                card=card,
                transactions=transactions,
                logs=logs,
            )
    finally:
        conn.close()


@app.route("/student/update_profile", methods=["POST"])
def student_update_profile():
    if "role" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    phone = request.form["phone"]
    email = request.form["email"]
    password = request.form["password"]

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE Students SET phone=%s, email=%s WHERE user_id=%s",
                (phone, email, session["user_id"]),
            )
            if password:
                cursor.execute(
                    "UPDATE Users SET password=%s WHERE user_id=%s",
                    (password, session["user_id"]),
                )
        conn.commit()
        flash("Profile updated successfully")
    except Exception as e:
        conn.rollback()
        flash(f"Error updating profile: {str(e)}")
    finally:
        conn.close()

    return redirect(url_for("student_dashboard"))

    
from datetime import datetime

@app.route("/student/transaction", methods=["POST"])
def student_transaction():
    if "role" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    trans_type = request.form["trans_type"]  # 'payment' or 'recharge'
    try:
        amount = float(request.form["amount"])
    except Exception:
        flash("Invalid amount")
        return redirect(url_for("student_dashboard"))

    merchant = request.form.get("merchant", "").strip()

    # 接收用户时间（可为空）
    user_time_raw = request.form.get("time", "").strip()

    # 允许的时间解析格式列表（按优先级）
    parse_formats = [
        "%Y-%m-%dT%H:%M:%S",  # e.g. 2025-12-14T12:35:17
        "%Y-%m-%dT%H:%M",     # e.g. 2025-12-14T12:35
        "%Y-%m-%d %H:%M:%S",  # e.g. 2025-12-14 12:35:17
        "%Y-%m-%d %H:%M",     # e.g. 2025-12-14 12:35
        "%Y-%m-%d",           # just date (will set time to 00:00:00)
    ]

    user_time = None
    if user_time_raw:
        parsed = None
        for fmt in parse_formats:
            try:
                parsed = datetime.strptime(user_time_raw, fmt)
                break
            except Exception:
                continue

        if not parsed:
            # 更友好的提示，包含示例
            flash(
                "Invalid time format. Acceptable examples: "
                "2025-12-14T12:35, 2025-12-14T12:35:17, "
                "2025-12-14 12:35, 2025-12-14 12:35:17, or leave blank for now."
            )
            return redirect(url_for("student_dashboard"))

        # 如果用户只输入日期，默认时间 00:00:00（可按需改）
        # 格式化为 MySQL DATETIME 字符串
        user_time = parsed.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 获取卡信息
            cursor.execute(
                "SELECT card_id, balance FROM Cards WHERE user_id=%s",
                (session["user_id"],),
            )
            card = cursor.fetchone()
            if not card:
                flash("Card not found")
                return redirect(url_for("student_dashboard"))

            # 余额计算
            if trans_type == "payment":
                if float(card["balance"]) < amount:
                    flash("Insufficient balance")
                    return redirect(url_for("student_dashboard"))
                new_balance = float(card["balance"]) - amount
                if not merchant:
                    merchant = "Unknown Merchant"
            else:  # recharge
                new_balance = float(card["balance"]) + amount
                merchant = "Recharge"

            # 插入记录：如果 user_time 有值就使用该时间，否则使用 NOW()
            if user_time:
                cursor.execute(
                    """
                    INSERT INTO Transactions (card_id, trans_type, amount, merchant_name, time)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (card["card_id"], trans_type, amount, merchant, user_time),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO Transactions (card_id, trans_type, amount, merchant_name, time)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (card["card_id"], trans_type, amount, merchant),
                )

            # 更新余额
            cursor.execute(
                "UPDATE Cards SET balance=%s WHERE card_id=%s",
                (new_balance, card["card_id"]),
            )

        conn.commit()
        flash("Transaction successful")
    except Exception as e:
        conn.rollback()
        flash(f"Transaction failed: {str(e)}")
    finally:
        conn.close()

    return redirect(url_for("student_dashboard"))

# All Transactions
@app.route("/student/all_transactions")
def student_all_transactions():
    if "role" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Card Info
            cursor.execute("SELECT * FROM Cards WHERE user_id = %s", (session["user_id"],))
            card = cursor.fetchone()

            # All Transactions
            cursor.execute(
                "SELECT * FROM Transactions WHERE card_id = %s ORDER BY time DESC",
                (card["card_id"],)
            )
            transactions = cursor.fetchall()

            return render_template("student_all_transactions.html", transactions=transactions)
    finally:
        conn.close()


# All Access Logs
@app.route("/student/all_access_logs")
def student_all_access_logs():
    if "role" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Card Info
            cursor.execute("SELECT * FROM Cards WHERE user_id = %s", (session["user_id"],))
            card = cursor.fetchone()

            # All Access Logs
            cursor.execute("""
                SELECT al.*, ap.building_name 
                FROM AccessLogs al 
                JOIN AccessPoints ap ON al.point_id = ap.point_id 
                WHERE card_id = %s ORDER BY time DESC
            """, (card["card_id"],))
            logs = cursor.fetchall()

            return render_template("student_all_access_logs.html", logs=logs)
    finally:
        conn.close()


# --- Faculty Routes ---
@app.route("/faculty")
def faculty_dashboard():
    if "role" not in session or session["role"] != "faculty":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ===== 1. Faculty Basic Info =====
            cursor.execute(
                "SELECT * FROM Faculty WHERE user_id = %s", (session["user_id"],)
            )
            faculty = cursor.fetchone()

            # ===== 2. Faculty Card Info =====
            cursor.execute(
                "SELECT * FROM Cards WHERE user_id = %s", (session["user_id"],)
            )
            card = cursor.fetchone()

            # ===== 3. Department Financial Stats =====
            cursor.execute(
                """
                SELECT COUNT(*) as count, SUM(amount) as total 
                FROM Transactions t
                JOIN Cards c ON t.card_id = c.card_id
                JOIN Students s ON c.user_id = s.user_id
                WHERE s.department = %s AND t.trans_type = 'payment'
                """,
                (faculty["department"],),
            )
            dept_stats = cursor.fetchone()

            # ===== 4. Department Access Stats (修复后的版本) =====
            cursor.execute(
                """
                SELECT 
                    COUNT(*) AS count,
                    COUNT(DISTINCT s.user_id) AS users,
                    (
                        SELECT ap.building_name
                        FROM AccessLogs al2
                        JOIN Cards c2 ON al2.card_id = c2.card_id
                        JOIN Students s2 ON c2.user_id = s2.user_id
                        JOIN AccessPoints ap ON al2.point_id = ap.point_id
                        WHERE s2.department = %s
                        GROUP BY ap.building_name
                        ORDER BY COUNT(*) DESC
                        LIMIT 1
                    ) AS top_location
                FROM AccessLogs al
                JOIN Cards c ON al.card_id = c.card_id
                JOIN Students s ON c.user_id = s.user_id
                WHERE s.department = %s;
                """,
                (faculty["department"], faculty["department"])
            )
            dept_access_stats = cursor.fetchone()


            # ===== 5. Faculty Personal Transactions =====
            cursor.execute(
                "SELECT * FROM Transactions WHERE card_id = %s ORDER BY time DESC LIMIT 5",
                (card["card_id"],),
            )
            personal_transactions = cursor.fetchall()

            # ===== 6. Faculty Personal Access Logs =====
            cursor.execute(
                """
                SELECT al.*, ap.building_name 
                FROM AccessLogs al 
                JOIN AccessPoints ap ON al.point_id = ap.point_id 
                WHERE card_id = %s ORDER BY time DESC LIMIT 5
                """,
                (card["card_id"],),
            )
            personal_logs = cursor.fetchall()

            # ===== 7. Department Students (Card Management) =====
            cursor.execute(
                """
                SELECT s.student_id, s.name, c.card_id, c.status, c.balance
                FROM Students s
                JOIN Cards c ON s.user_id = c.user_id
                WHERE s.department = %s
                """,
                (faculty["department"],),
            )
            dept_students = cursor.fetchall()

            # ===== 8. Render Template =====
            return render_template(
                "faculty_dashboard.html",
                faculty=faculty,
                card=card,
                dept_stats=dept_stats,
                dept_access_stats=dept_access_stats,   # <<< 必须传给模板
                dept_students=dept_students,
                personal_transactions=personal_transactions,
                personal_logs=personal_logs,
            )
    finally:
        conn.close()

# All Faculty Transactions
@app.route("/faculty/all_transactions")
def faculty_all_transactions():
    if "role" not in session or session["role"] != "faculty":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Faculty Card
            cursor.execute("SELECT * FROM Cards WHERE user_id = %s", (session["user_id"],))
            card = cursor.fetchone()

            # All Transactions
            cursor.execute(
                "SELECT * FROM Transactions WHERE card_id = %s ORDER BY time DESC",
                (card["card_id"],)
            )
            transactions = cursor.fetchall()

            return render_template("faculty_all_transactions.html", transactions=transactions)
    finally:
        conn.close()


# All Faculty Access Logs
@app.route("/faculty/all_access_logs")
def faculty_all_access_logs():
    if "role" not in session or session["role"] != "faculty":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Faculty Card
            cursor.execute("SELECT * FROM Cards WHERE user_id = %s", (session["user_id"],))
            card = cursor.fetchone()

            # All Access Logs
            cursor.execute("""
                SELECT al.*, ap.building_name 
                FROM AccessLogs al 
                JOIN AccessPoints ap ON al.point_id = ap.point_id 
                WHERE card_id = %s ORDER BY time DESC
            """, (card["card_id"],))
            logs = cursor.fetchall()

            return render_template("faculty_all_access_logs.html", logs=logs)
    finally:
        conn.close()


@app.route("/faculty/update_profile", methods=["POST"])
def faculty_update_profile():
    if "role" not in session or session["role"] != "faculty":
        return redirect(url_for("login"))

    phone = request.form["phone"]
    email = request.form["email"]
    password = request.form["password"]

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE Faculty SET phone=%s, email=%s WHERE user_id=%s",
                (phone, email, session["user_id"]),
            )
            if password:
                cursor.execute(
                    "UPDATE Users SET password=%s WHERE user_id=%s",
                    (password, session["user_id"]),
                )
        conn.commit()
        flash("Profile updated successfully")
    except Exception as e:
        conn.rollback()
        flash(f"Error updating profile: {str(e)}")
    finally:
        conn.close()

    return redirect(url_for("faculty_dashboard"))


@app.route("/faculty/update_card_status", methods=["POST"])
def faculty_update_card_status():
    if "role" not in session or session["role"] != "faculty":
        return redirect(url_for("login"))

    card_id = request.form["card_id"]
    new_status = request.form["status"]

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 验证学生属于本学院
            cursor.execute(
                "SELECT department FROM Faculty WHERE user_id=%s", (session["user_id"],)
            )
            faculty_dept = cursor.fetchone()["department"]

            cursor.execute(
                """
                SELECT s.department 
                FROM Cards c 
                JOIN Students s ON c.user_id = s.user_id 
                WHERE c.card_id = %s
            """, (card_id,))
            student = cursor.fetchone()

            if student and student["department"] == faculty_dept:
                # 插入请求表
                cursor.execute(
                    """
                    INSERT INTO CardStatusRequests (card_id, requested_by, new_status)
                    VALUES (%s, %s, %s)
                    """, (card_id, session["user_id"], new_status)
                )
                conn.commit()
                flash("Request submitted for admin approval", "success")
            else:
                flash("Unauthorized operation", "danger")

    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("faculty_dashboard"))


@app.route("/faculty/export_report")
def faculty_export_report():
    if "role" not in session or session["role"] != "faculty":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT department FROM Faculty WHERE user_id=%s", (session["user_id"],)
            )
            dept = cursor.fetchone()["department"]

            cursor.execute(
                """
                SELECT s.student_id, s.name, t.time, t.merchant_name, t.amount
                FROM Transactions t
                JOIN Cards c ON t.card_id = c.card_id
                JOIN Students s ON c.user_id = s.user_id
                WHERE s.department = %s
                ORDER BY t.time DESC
            """,
                (dept,),
            )
            transactions = cursor.fetchall()

            si = io.StringIO()
            cw = csv.writer(si)
            cw.writerow(["Student ID", "Name", "Time", "Merchant", "Amount"])
            for t in transactions:
                cw.writerow(
                    [
                        t["student_id"],
                        t["name"],
                        t["time"],
                        t["merchant_name"],
                        t["amount"],
                    ]
                )

            output = make_response(si.getvalue())
            output.headers["Content-Disposition"] = "attachment; filename=export.csv"
            output.headers["Content-type"] = "text/csv"
            return output
    finally:
        conn.close()

@app.route("/faculty/export_access_report")
def faculty_export_access_report():
    if "role" not in session or session["role"] != "faculty":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:

            # ① 获取教师所属学院
            cursor.execute(
                "SELECT department FROM Faculty WHERE user_id=%s",
                (session["user_id"],)
            )
            dept = cursor.fetchone()["department"]

            # ② 查询该院学生的通行记录
            cursor.execute(
                """
                SELECT 
                    s.student_id,
                    s.name,
                    a.time,
                    ap.building_name AS location,
                    a.direction
                FROM AccessLogs a
                JOIN Cards c ON a.card_id = c.card_id
                JOIN Students s ON c.user_id = s.user_id
                JOIN AccessPoints ap ON a.point_id = ap.point_id
                WHERE s.department = %s
                ORDER BY a.time DESC
                """,
                (dept,)
            )
            access_records = cursor.fetchall()

            # ③ 写入 CSV
            si = io.StringIO()
            cw = csv.writer(si)
            cw.writerow(["Student ID", "Name", "Time", "Direction", "Location"])

            for r in access_records:
                cw.writerow([
                    r["student_id"],
                    r["name"],
                    r["time"],
                    r["direction"],
                    r["location"],
                ])

            # ④ 返回 CSV 文件
            output = make_response(si.getvalue())
            output.headers["Content-Disposition"] = "attachment; filename=access_report.csv"
            output.headers["Content-Type"] = "text/csv"
            return output

    finally:
        conn.close()


# --- Admin Routes ---
@app.route("/admin")
def admin_dashboard():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")

@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == "POST":
                action = request.form["action"]
                
                # -------------------------
                # 删除用户
                # -------------------------
                if action == "delete":
                    user_id = request.form["user_id"]

                    # 1. 找到该用户的卡片
                    cursor.execute("SELECT card_id FROM Cards WHERE user_id=%s", (user_id,))
                    cards = cursor.fetchall()
                    card_ids = [c['card_id'] for c in cards]

                    # 2. 删除 AccessLogs 中对应卡片的记录
                    if card_ids:
                        format_strings = ','.join(['%s'] * len(card_ids))
                        cursor.execute(f"DELETE FROM AccessLogs WHERE card_id IN ({format_strings})", tuple(card_ids))

                    # 3. 删除 Cards
                    cursor.execute("DELETE FROM Cards WHERE user_id=%s", (user_id,))

                    # 4. 删除 AccessRights 中 role_value 对应的条目（学生或教师）
                    cursor.execute("SELECT role FROM Users WHERE user_id=%s", (user_id,))
                    role = cursor.fetchone()["role"]
                    if role == "student":
                        cursor.execute("DELETE FROM AccessRights WHERE role_value IN (SELECT student_id FROM Students WHERE user_id=%s)", (user_id,))
                    elif role == "faculty":
                        cursor.execute("DELETE FROM AccessRights WHERE role_value IN (SELECT staff_id FROM Faculty WHERE user_id=%s)", (user_id,))

                    # 5. 删除学生/教师表条目（由于外键 ON DELETE CASCADE 可选）
                    cursor.execute("DELETE FROM Students WHERE user_id=%s", (user_id,))
                    cursor.execute("DELETE FROM Faculty WHERE user_id=%s", (user_id,))

                    # 6. 删除用户
                    cursor.execute("DELETE FROM Users WHERE user_id=%s", (user_id,))
                    conn.commit()

                    flash("User and all related records deleted", "success")


                # -------------------------
                # 添加用户
                # -------------------------
                elif action == "add":
                    username = request.form["username"]
                    password = request.form["password"]
                    role = request.form["role"]

                    # --- Check username duplicate ---
                    cursor.execute("SELECT user_id FROM Users WHERE username=%s", (username,))
                    existing = cursor.fetchone()

                    if existing:
                        flash("Username already exists. Choose another one.", "danger")
                    else:
                        # Insert base user
                        cursor.execute(
                            "INSERT INTO Users (username, password, role) VALUES (%s, %s, %s)",
                            (username, password, role)
                        )
                        conn.commit()
                        user_id = cursor.lastrowid

                        # STUDENT
                        if role == "student":
                            cursor.execute("""
                                INSERT INTO Students
                                (student_id, user_id, name, gender, identity_card, department, phone, email, grade)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                request.form["student_id"],
                                user_id,
                                request.form["name"],
                                request.form["gender"],
                                request.form["identity_card"],
                                request.form["department"],
                                request.form.get("phone"),
                                request.form.get("email"),
                                request.form.get("grade", "2025")
                            ))
                            conn.commit()

                        # FACULTY
                        elif role == "faculty":
                            cursor.execute("""
                                INSERT INTO Faculty
                                (staff_id, user_id, name, gender, identity_card, department, phone, email)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                request.form["staff_id"],
                                user_id,
                                request.form["name"],
                                request.form["gender"],
                                request.form["identity_card"],
                                request.form["department"],
                                request.form.get("phone"),
                                request.form.get("email")
                            ))
                            conn.commit()

                        # 构造 card_id
                        if role == 'student':
                            card_id = "CARD" + request.form["student_id"]
                        else:  # faculty
                            card_id = "CARD" + request.form["staff_id"]

                        if role in ['student', 'faculty']:
                             # Create Card
                            cursor.execute(
                                "INSERT INTO Cards (card_id, user_id, status, balance, subsidy_balance, open_date) "
                                "VALUES (%s, %s, %s, %s, %s,  CURDATE())",
                                (card_id, user_id, 'frozen', 0.00, 0.00)
                            )
                            conn.commit()


                        flash(f"{role.capitalize()} added successfully")
                # -------------------------
                # EDIT USER  ⭐新增
                # -------------------------
                elif action == "edit":
                    user_id = request.form["user_id"]
                    username = request.form["username"]
                    password = request.form["password"]

                    # 1. Update Users table
                    cursor.execute("""
                        UPDATE Users SET username=%s, password=%s
                        WHERE user_id=%s
                    """, (username, password, user_id))
                    conn.commit()

                    # 2. Query role
                    cursor.execute("SELECT role FROM Users WHERE user_id=%s", (user_id,))
                    role = cursor.fetchone()["role"]

                    # 3. Student update
                    if role == "student":
                        cursor.execute("""
                            UPDATE Students SET
                                name=%s,
                                gender=%s,
                                identity_card=%s,
                                department=%s,
                                phone=%s,
                                email=%s,
                                grade=%s
                            WHERE user_id=%s
                        """, (
                            request.form["name"], request.form["gender"],
                            request.form["identity_card"], request.form["department"],
                            request.form["phone"], request.form["email"],
                            request.form["grade"], user_id
                        ))

                    # 4. Faculty update
                    elif role == "faculty":
                        cursor.execute("""
                            UPDATE Faculty SET
                                name=%s,
                                gender=%s,
                                identity_card=%s,
                                department=%s,
                                phone=%s,
                                email=%s
                            WHERE user_id=%s
                        """, (
                            request.form["name"], request.form["gender"],
                            request.form["identity_card"], request.form["department"],
                            request.form["phone"], request.form["email"], user_id
                        ))

                    conn.commit()
                    flash("User information updated.", "success")
            # =======================
            # 查询用户详细信息（保持不变）
            # =======================
            cursor.execute("""
                SELECT u.user_id, u.username, u.password, u.role,
                       s.student_id, s.name AS student_name, s.gender AS student_gender, s.identity_card AS student_id_card, 
                       s.department AS student_dept, s.phone AS student_phone, s.email AS student_email, s.grade AS student_grade,
                       f.staff_id, f.name AS faculty_name, f.gender AS faculty_gender, f.identity_card AS faculty_id_card, 
                       f.department AS faculty_dept, f.phone AS faculty_phone, f.email AS faculty_email
                FROM Users u
                LEFT JOIN Students s ON u.user_id = s.user_id
                LEFT JOIN Faculty f ON u.user_id = f.user_id
                ORDER BY u.user_id
            """)
            users = cursor.fetchall()

            return render_template("admin_users.html", users=users)

    finally:
        conn.close()


@app.route("/admin/cards", methods=["GET", "POST"])
def admin_cards():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:

            # ====== Handle update ======
            if request.method == "POST":
                action = request.form.get("action")

                if action == "update":
                    old_card_id = request.form.get("old_card_id")
                    card_id = request.form.get("card_id")  # 新的 card_id
                    status = request.form.get("status")
                    open_date = request.form.get("open_date")
                    balance = request.form.get("balance")
                    subsidy = request.form.get("subsidy_balance")

                    cursor.execute("""
                        UPDATE Cards
                        SET card_id=%s,
                            status=%s,
                            open_date=%s,
                            balance=%s,
                            subsidy_balance=%s
                        WHERE card_id=%s
                    """, (card_id, status, open_date, balance, subsidy, old_card_id))

                    conn.commit()
                    flash("Card updated successfully!", "success")


            # ====== Query cards with user info ======
            cursor.execute("""
                SELECT 
                    c.card_id, c.user_id, c.status, c.balance, c.subsidy_balance, c.open_date,
                    u.role,

                    s.student_id, s.name AS student_name, s.gender AS student_gender,
                    s.department AS student_dept,

                    f.staff_id, f.name AS faculty_name, f.gender AS faculty_gender,
                    f.department AS faculty_dept

                FROM Cards c
                JOIN Users u ON c.user_id = u.user_id
                LEFT JOIN Students s ON u.user_id = s.user_id
                LEFT JOIN Faculty f ON u.user_id = f.user_id

                ORDER BY c.card_id
            """)

            cards = cursor.fetchall()

            return render_template("admin_cards.html", cards=cards)

    finally:
        conn.close()
@app.route("/admin/card_requests", methods=["GET", "POST"])
def admin_card_requests():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == "POST":
                request_id = request.form["request_id"]
                action = request.form["action"]

                if action == "approve":
                    cursor.execute("SELECT card_id, new_status FROM CardStatusRequests WHERE request_id=%s", (request_id,))
                    req = cursor.fetchone()
                    # 更新卡片状态
                    cursor.execute("UPDATE Cards SET status=%s WHERE card_id=%s", (req["new_status"], req["card_id"]))
                    # 更新请求状态
                    cursor.execute("""
                        UPDATE CardStatusRequests
                        SET status='approved', approved_by=%s, approved_time=NOW()
                        WHERE request_id=%s
                    """, (session["user_id"], request_id))

                elif action == "reject":
                    cursor.execute("""
                        UPDATE CardStatusRequests
                        SET status='rejected', approved_by=%s, approved_time=NOW()
                        WHERE request_id=%s
                    """, (session["user_id"], request_id))

                conn.commit()

            # 查询待审批请求
            cursor.execute("""
                SELECT r.*, u.username AS faculty_name, c.card_id
                FROM CardStatusRequests r
                JOIN Users u ON r.requested_by = u.user_id
                JOIN Cards c ON r.card_id = c.card_id
                WHERE r.status='pending'
                ORDER BY r.request_time DESC
            """)
            requests = cursor.fetchall()

            return render_template("admin_card_requests.html", requests=requests)

    finally:
        conn.close()




ACADEMIC_DEPTS = ["智能学院", "计算机学院", "数学学院", "物理学院"]
NON_ACADEMIC_DEPTS = ["学工部", "校务部", "后勤部", "保卫处"]

@app.route("/admin/points", methods=["GET", "POST"])
def admin_points():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == "POST":
                action = request.form.get("action")

                # ===== Add =====
                if action == "add":
                    pid = request.form["point_id"]
                    name = request.form["building_name"]
                    dept = request.form["manager_dept"]

                    # 先检查是否存在
                    cursor.execute("SELECT 1 FROM AccessPoints WHERE point_id=%s", (pid,))
                    if cursor.fetchone():
                        flash(f"Point ID {pid} already exists!", "danger")
                    else:
                        cursor.execute(
                            "INSERT INTO AccessPoints(point_id, building_name, manager_dept_id) VALUES (%s, %s, %s)",
                            (pid, name, dept),
                        )
                        conn.commit()
                        flash(f"Point {pid} added successfully!", "success")


                # ===== Delete =====
                elif action == "delete":
                    pid = request.form["point_id"]
                    cursor.execute("DELETE FROM AccessPoints WHERE point_id=%s", (pid,))
                    conn.commit()

                # ===== Update =====
                elif action == "update":
                    old_pid = request.form["old_point_id"]
                    pid = request.form["point_id"]
                    name = request.form["building_name"]
                    dept = request.form["manager_dept"]

                    if pid != old_pid:
                        # 检查新的ID是否已经存在
                        cursor.execute("SELECT 1 FROM AccessPoints WHERE point_id=%s", (pid,))
                        if cursor.fetchone():
                            flash(f"Point ID {pid} already exists!", "danger")
                            return redirect(url_for("admin_points"))

                    cursor.execute("""
                        UPDATE AccessPoints
                        SET point_id=%s, building_name=%s, manager_dept_id=%s
                        WHERE point_id=%s
                    """, (pid, name, dept, old_pid))
                    conn.commit()
                    flash(f"Point {old_pid} updated successfully!", "success")


            cursor.execute("SELECT * FROM AccessPoints")
            points = cursor.fetchall()
            return render_template(
                "admin_points.html",
                points=points,
                academic_depts=ACADEMIC_DEPTS,
                non_academic_depts=NON_ACADEMIC_DEPTS
            )
    finally:
        conn.close()


# --- Admin Terminals ---
@app.route("/admin/terminals", methods=["GET", "POST"])
def admin_terminals():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == "POST":
                action = request.form["action"]
                terminal_id = request.form["terminal_id"]
                merchant_name = request.form.get("merchant_name")
                category = request.form.get("category")
                charge_rule = request.form.get("charge_rule")
                manager_dept = request.form.get("manager_dept")

                if action == "add":
                    cursor.execute(
                        "INSERT INTO Terminals (terminal_id, merchant_name, category, charge_rule, manager_dept) VALUES (%s, %s, %s, %s, %s)",
                        (terminal_id, merchant_name, category, charge_rule, manager_dept)
                    )
                    conn.commit()
                    flash("Terminal added successfully")
                elif action == "update":
                    cursor.execute(
                        "UPDATE Terminals SET merchant_name=%s, category=%s, charge_rule=%s, manager_dept=%s WHERE terminal_id=%s",
                        (merchant_name, category, charge_rule, manager_dept, terminal_id)
                    )
                    conn.commit()
                    flash("Terminal updated successfully")
                elif action == "delete":
                    cursor.execute(
                        "DELETE FROM Terminals WHERE terminal_id=%s",
                        (terminal_id,)
                    )
                    conn.commit()
                    flash("Terminal deleted successfully")

            cursor.execute("SELECT * FROM Terminals")
            terminals = cursor.fetchall()
            return render_template("admin_terminals.html", terminals=terminals)
    finally:
        conn.close()


# --- Admin Access Rights ---
@app.route("/admin/access_rights", methods=["GET", "POST"])
def admin_access_rights():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == "POST":
                action = request.form["action"]
                role_type = request.form["role_type"]
                role_value = request.form["role_value"]
                point_id = request.form["point_id"]

                if action == "add":
                    cursor.execute(
                        "INSERT INTO AccessRights (role_type, role_value, point_id) VALUES (%s, %s, %s)",
                        (role_type, role_value, point_id)
                    )
                    conn.commit()
                    flash("Access right added")
                elif action == "delete":
                    cursor.execute(
                        "DELETE FROM AccessRights WHERE role_type=%s AND role_value=%s AND point_id=%s",
                        (role_type, role_value, point_id)
                    )
                    conn.commit()
                    flash("Access right removed")

            # 查询 AccessRights 并关联姓名和建筑
            cursor.execute("""
                SELECT ar.role_type, ar.role_value, ar.point_id,
                       s.name AS student_name, f.name AS faculty_name, ap.building_name
                FROM AccessRights ar
                LEFT JOIN Students s ON ar.role_type='student' AND ar.role_value=s.student_id
                LEFT JOIN Faculty f ON ar.role_type='faculty' AND ar.role_value=f.staff_id
                LEFT JOIN AccessPoints ap ON ar.point_id=ap.point_id
            """)
            rights = cursor.fetchall()

            cursor.execute("SELECT student_id, name FROM Students")
            students = cursor.fetchall()
            cursor.execute("SELECT staff_id, name FROM Faculty")
            faculty = cursor.fetchall()
            cursor.execute("SELECT * FROM AccessPoints")
            points = cursor.fetchall()

            return render_template(
                "admin_access_rights.html",
                rights=rights,
                students=students,
                faculty=faculty,
                points=points
            )
    finally:
        conn.close()



@app.route("/admin/query/<int:query_id>")
def admin_query(query_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    results = []
    columns = []
    sql = ""

    try:
        with conn.cursor() as cursor:
            if query_id == 1:
                # Query 1: Wang X Ming
                sql = """
                    SELECT s.name, SUM(t.amount) as total
                    FROM Students s
                    JOIN Cards c ON s.user_id = c.user_id
                    JOIN Transactions t ON c.card_id = t.card_id
                    WHERE s.name LIKE '王_明%' AND CHAR_LENGTH(s.name) >= 3 AND t.time <= '2025-12-21 23:59:59'
                    GROUP BY s.student_id
                """
            elif query_id == 2:
                # Query 2: Below Avg
                sql = """
                    WITH GlobalAvg AS (SELECT AVG(amount) as avg_amt FROM Transactions WHERE trans_type = 'payment'),
                    UserAvg AS (
                        SELECT u.username, AVG(t.amount) as user_avg_amt
                        FROM Users u
                        JOIN Cards c ON u.user_id = c.user_id
                        JOIN Transactions t ON c.card_id = t.card_id
                        WHERE t.trans_type = 'payment'
                        GROUP BY u.user_id
                    )
                    SELECT ua.username, ua.user_avg_amt
                    FROM UserAvg ua JOIN GlobalAvg ga
                    WHERE ua.user_avg_amt < ga.avg_amt
                    ORDER BY ua.user_avg_amt DESC
                """
            elif query_id == 3:
                # Query 3: Top 10 Spenders
                sql = """
                    SELECT 
                        COALESCE(s.name, f.name) as name,
                        COALESCE(s.phone, f.phone) as phone,
                        COUNT(*) as trans_count,
                        SUM(t.amount) as total_amount
                    FROM Users u
                    LEFT JOIN Students s ON u.user_id = s.user_id
                    LEFT JOIN Faculty f ON u.user_id = f.user_id
                    JOIN Cards c ON u.user_id = c.user_id
                    JOIN Transactions t ON c.card_id = t.card_id
                    WHERE t.time >= '2025-12-15 00:00:00'
                      AND t.trans_type = 'payment'
                    GROUP BY u.user_id
                    ORDER BY total_amount DESC
                    LIMIT 10
                """
            elif query_id == 4:
                # Query 4: Busiest Access Point
                sql = """
                    SELECT 
                        ap.manager_dept_id,
                        COUNT(*) as access_count
                    FROM AccessLogs al
                    JOIN AccessPoints ap ON al.point_id = ap.point_id
                    WHERE al.time <= '2025-12-21 23:59:59'
                    GROUP BY ap.point_id
                    ORDER BY access_count DESC
                    LIMIT 1
                """
            elif query_id == 5:
                # Query 5: Smart Dept Max Merchant
                sql = """
                    WITH DailyMerchantAvg AS (
                        SELECT 
                            t.merchant_name,
                            DATE(t.time) as trans_date,
                            AVG(t.amount) as avg_amount
                        FROM Transactions t
                        JOIN Cards c ON t.card_id = c.card_id
                        JOIN Students s ON c.user_id = s.user_id
                        WHERE s.department = '智能学院'
                          AND t.time BETWEEN '2025-12-14 00:00:00' AND '2025-12-19 23:59:59'
                          AND t.trans_type = 'payment'
                        GROUP BY t.merchant_name, DATE(t.time)
                        ORDER BY avg_amount DESC
                        LIMIT 1
                    )
                    SELECT t.* 
                    FROM Transactions t
                    JOIN DailyMerchantAvg dma ON t.merchant_name = dma.merchant_name
                    WHERE t.time BETWEEN '2025-12-14 00:00:00' AND '2025-12-19 23:59:59'
                """
            elif query_id == 6:
                # Query 6: High Frequency Users
                sql = """
                    WITH SmartDeptStats AS (
                        SELECT 
                            DATE(t.time) as t_date,
                            COUNT(*) / (SELECT COUNT(*) FROM Students WHERE department = '智能学院') as avg_daily_count
                        FROM Transactions t
                        JOIN Cards c ON t.card_id = c.card_id
                        JOIN Students s ON c.user_id = s.user_id
                        WHERE s.department = '智能学院'
                          AND t.trans_type = 'payment'
                        GROUP BY DATE(t.time)
                    ),
                    UserDailyStats AS (
                        SELECT 
                            u.user_id,
                            DATE(t.time) as t_date,
                            COUNT(*) as user_count
                        FROM Users u
                        JOIN Cards c ON u.user_id = c.user_id
                        JOIN Transactions t ON c.card_id = t.card_id
                        WHERE t.trans_type = 'payment'
                        GROUP BY u.user_id, DATE(t.time)
                    )
                    SELECT 
                        COALESCE(s.name, f.name) as name,
                        COALESCE(s.student_id, f.staff_id) as id_num,
                        COALESCE(s.department, f.department) as dept,
                        uds.t_date,
                        uds.user_count
                    FROM UserDailyStats uds
                    JOIN SmartDeptStats sds ON uds.t_date = sds.t_date
                    LEFT JOIN Students s ON uds.user_id = s.user_id
                    LEFT JOIN Faculty f ON uds.user_id = f.user_id
                    WHERE uds.user_count >= 2 * sds.avg_daily_count
                """
            elif query_id == 7:
                # Query 7: CS Dept Night Access
                sql = """
                    SELECT 
                        s.name,
                        COUNT(*) as night_access_count
                    FROM AccessLogs al
                    JOIN Cards c ON al.card_id = c.card_id
                    JOIN Students s ON c.user_id = s.user_id
                    JOIN AccessPoints ap ON al.point_id = ap.point_id
                    WHERE s.department = '计算机学院'
                      AND ap.building_name LIKE '理科二号楼%'
                      AND (TIME(al.time) >= '22:00:00' OR TIME(al.time) <= '06:00:00')
                    GROUP BY s.student_id
                    ORDER BY night_access_count DESC, s.name ASC
                """

            if sql:
                cursor.execute(sql)
                results = cursor.fetchall()
                if results:
                    columns = results[0].keys()

    finally:
        conn.close()

    return render_template(
        "query_result.html", results=results, columns=columns, query_id=query_id
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
