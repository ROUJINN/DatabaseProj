# Smart Campus System (智慧校园一卡通系统)

## 1. Project Overview
This project is a database course internship assignment implementing a Smart Campus Card System. It includes database design, data generation, a Web application (Flask), and Big Data analysis (Hadoop MapReduce).

## 2. Directory Structure
```
database/
├── app/                # Web Application
│   ├── templates/      # HTML Templates
│   └── app.py          # Flask Main Application
├── doc/                # Documentation
├── mapreduce/          # Hadoop MapReduce Scripts
│   ├── mapper_1.py
│   ├── reducer_1.py
│   ├── mapper_2.py
│   └── reducer_2.py
├── scripts/            # Utility Scripts
│   ├── generate_data.py # Data Generator
│   └── export_logs.py   # Export DB logs to file
├── sql/                # SQL Files
│   ├── schema.sql      # Database Schema
│   ├── data.sql        # Generated Data (Output of generate_data.py)
│   └── queries.sql     # Required SQL Queries
└── README.md
```

## 3. Setup & Installation

### 3.1 Prerequisites
*   Python 3.8+
*   MySQL 8.0+
*   Hadoop 3.3+ (for MapReduce tasks)

### 3.2 Python Dependencies
```bash
pip install flask pymysql faker
```

### 3.3 Database Setup
1.  Create the database and tables:
    ```bash
    mysql -u root -p < sql/schema.sql
    ```
2.  Generate mock data:
    ```bash
    python3 scripts/generate_data.py
    ```
    This will create `sql/data.sql`.
3.  Import data:
    ```bash
    mysql -u root -p smart_campus < sql/data.sql
    ```

## 4. Running the Web Application
1.  Edit `app/app.py` and update the `db_config` dictionary with your MySQL password.
2.  Run the app:
    ```bash
    python3 app/app.py
    ```
3.  Open browser at `http://localhost:5000`.
    *   **Admin Login**: username `admin`, password `admin123`
    *   **Student Login**: username `stu0`, password `123456`
    *   **Faculty Login**: username `fac0`, password `123456`

## 5. Running MapReduce Tasks

### 5.1 Prepare Data
Export logs from MySQL to a text file:
```bash
python3 scripts/export_logs.py
# Generates access.log
```

### 5.2 Run Hadoop Streaming
Make sure Hadoop is running (`start-dfs.sh`, `start-yarn.sh`).

**Task 1: Count Operations**
```bash
hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
    -input /input/access.log \
    -output /output/task1 \
    -mapper "python3 $(pwd)/mapreduce/mapper_1.py" \
    -reducer "python3 $(pwd)/mapreduce/reducer_1.py" \
    -file $(pwd)/mapreduce/mapper_1.py \
    -file $(pwd)/mapreduce/reducer_1.py
```

**Task 2: User Statistics (Top 10)**
```bash
hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
    -input /input/access.log \
    -output /output/task2_raw \
    -mapper "python3 $(pwd)/mapreduce/mapper_2.py" \
    -reducer "python3 $(pwd)/mapreduce/reducer_2.py" \
    -file $(pwd)/mapreduce/mapper_2.py \
    -file $(pwd)/mapreduce/reducer_2.py

# Get Top 10 (Local processing of result)
hdfs dfs -cat /output/task2_raw/* | sort -nr | head -n 10
```

## 6. SQL Queries
The complex SQL queries required by the assignment are located in `sql/queries.sql`. You can run them directly in your SQL client or view them via the Admin Dashboard in the Web App.
