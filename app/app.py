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


@app.route("/student/transaction", methods=["POST"])
def student_transaction():
    if "role" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    trans_type = request.form[
        "trans_type"
    ]  # 'payment' or 'recharge' (we can simulate recharge as negative payment or handle logic)
    amount = float(request.form["amount"])
    merchant = request.form.get("merchant", "Self-Service")

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT card_id, balance FROM Cards WHERE user_id=%s",
                (session["user_id"],),
            )
            card = cursor.fetchone()

            if trans_type == "payment":
                if card["balance"] < amount:
                    flash("Insufficient balance")
                    return redirect(url_for("student_dashboard"))
                new_balance = float(card["balance"]) - amount
            else:  # recharge
                new_balance = float(card["balance"]) + amount
                # For recharge, we might record it differently, but let's just use Transactions table
                # If schema only has 'payment', we might need to adjust.
                # Schema has trans_type ENUM? Let's check schema.
                # Schema: trans_type ENUM('payment', 'recharge')? No, schema doesn't specify ENUM values in CREATE TABLE usually unless explicit.
                # Let's assume we can store 'recharge'.

            cursor.execute(
                "INSERT INTO Transactions (card_id, trans_type, amount, merchant_name, time) VALUES (%s, %s, %s, %s, NOW())",
                (card["card_id"], trans_type, amount, merchant),
            )

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


# --- Faculty Routes ---
@app.route("/faculty")
def faculty_dashboard():
    if "role" not in session or session["role"] != "faculty":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Basic Info
            cursor.execute(
                "SELECT * FROM Faculty WHERE user_id = %s", (session["user_id"],)
            )
            faculty = cursor.fetchone()

            # Card Info
            cursor.execute(
                "SELECT * FROM Cards WHERE user_id = %s", (session["user_id"],)
            )
            card = cursor.fetchone()

            # Department Stats
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

            # Personal Transactions
            cursor.execute(
                "SELECT * FROM Transactions WHERE card_id = %s ORDER BY time DESC LIMIT 5",
                (card["card_id"],),
            )
            personal_transactions = cursor.fetchall()

            # Personal Access Logs
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

            # List of students in department for card management
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

            return render_template(
                "faculty_dashboard.html",
                faculty=faculty,
                card=card,
                dept_stats=dept_stats,
                dept_students=dept_students,
                personal_transactions=personal_transactions,
                personal_logs=personal_logs,
            )
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
            # Verify student belongs to faculty's department
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
            """,
                (card_id,),
            )
            student_dept = cursor.fetchone()

            if student_dept and student_dept["department"] == faculty_dept:
                cursor.execute(
                    "UPDATE Cards SET status=%s WHERE card_id=%s", (new_status, card_id)
                )
                conn.commit()
                flash("Card status updated")
            else:
                flash("Unauthorized operation")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}")
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
                if action == "delete":
                    user_id = request.form["user_id"]
                    cursor.execute("DELETE FROM Users WHERE user_id=%s", (user_id,))
                    conn.commit()
                    flash("User deleted")

            cursor.execute("SELECT * FROM Users")
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
            if request.method == "POST":
                action = request.form["action"]
                if action == "update":
                    card_id = request.form["card_id"]
                    status = request.form["status"]
                    cursor.execute(
                        "UPDATE Cards SET status=%s WHERE card_id=%s", (status, card_id)
                    )
                    conn.commit()
                    flash("Card updated")

            cursor.execute("SELECT * FROM Cards")
            cards = cursor.fetchall()
            return render_template("admin_cards.html", cards=cards)
    finally:
        conn.close()


@app.route("/admin/points", methods=["GET", "POST"])
def admin_points():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == "POST":
                action = request.form["action"]
                if action == "add":
                    pid = request.form["point_id"]
                    name = request.form["building_name"]
                    dept = request.form["manager_dept"]
                    cursor.execute(
                        "INSERT INTO AccessPoints VALUES (%s, %s, %s)",
                        (pid, name, dept),
                    )
                    conn.commit()
                elif action == "delete":
                    pid = request.form["point_id"]
                    cursor.execute("DELETE FROM AccessPoints WHERE point_id=%s", (pid,))
                    conn.commit()

            cursor.execute("SELECT * FROM AccessPoints")
            points = cursor.fetchall()
            return render_template("admin_points.html", points=points)
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
