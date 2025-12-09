import datetime

import pymysql

# Database Configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "123456",  # UPDATE THIS
    "database": "smart_campus",
    "cursorclass": pymysql.cursors.DictCursor,
}


def export_logs():
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cursor:
            # Fetch Transactions
            cursor.execute("""
                SELECT t.time, u.username, 'pay' as op
                FROM Transactions t
                JOIN Cards c ON t.card_id = c.card_id
                JOIN Users u ON c.user_id = u.user_id
                WHERE t.trans_type = 'payment'
            """)
            transactions = cursor.fetchall()

            # Fetch Access Logs
            cursor.execute("""
                SELECT al.time, u.username, 
                       CASE WHEN al.direction = 'in' THEN 'access-in' ELSE 'access-out' END as op
                FROM AccessLogs al
                JOIN Cards c ON al.card_id = c.card_id
                JOIN Users u ON c.user_id = u.user_id
            """)
            access_logs = cursor.fetchall()

            all_logs = transactions + access_logs
            # Sort by time
            all_logs.sort(key=lambda x: x["time"])

            with open("access.log", "w", encoding="utf-8") as f:
                for log in all_logs:
                    # Format: 2025/12/20 20:50:12 Kagura query-funds
                    date_str = log["time"].strftime("%Y/%m/%d")
                    time_str = log["time"].strftime("%H:%M:%S")
                    line = f"{date_str}\t{time_str}\t{log['username']}\t{log['op']}\n"
                    f.write(line)

            print(f"Exported {len(all_logs)} logs to access.log")

    finally:
        conn.close()


if __name__ == "__main__":
    export_logs()
