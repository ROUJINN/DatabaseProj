import datetime

import pymysql
from flask import Flask, flash, redirect, render_template, request, session, url_for

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
                "SELECT * FROM Transactions WHERE card_id = %s ORDER BY time DESC LIMIT 5",
                (card["card_id"],),
            )
            transactions = cursor.fetchall()

            # Recent Access Logs
            cursor.execute(
                """
                SELECT al.*, ap.building_name 
                FROM AccessLogs al 
                JOIN AccessPoints ap ON al.point_id = ap.point_id 
                WHERE card_id = %s ORDER BY time DESC LIMIT 5
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

            # Department Stats (Example)
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

            return render_template(
                "faculty_dashboard.html",
                faculty=faculty,
                card=card,
                dept_stats=dept_stats,
            )
    finally:
        conn.close()


# --- Admin Routes ---
@app.route("/admin")
def admin_dashboard():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")


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
            # ... Add other queries here ...

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
