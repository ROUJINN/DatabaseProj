这是该 `README.md` 文件的中文翻译：

# Smart Campus System (智慧校园一卡通系统)

## 1. 项目概览
本项目是一个数据库课程实习作业，实现了一套智慧校园一卡通系统。项目内容包含数据库设计、数据生成、Web 应用程序 (Flask) 以及大数据分析 (Hadoop MapReduce)。

## 2. 目录结构
```
database/
├── app/                # Web 应用程序
│   ├── templates/      # HTML 模板
│   └── app.py          # Flask 主程序
├── doc/                # 文档
├── mapreduce/          # Hadoop MapReduce 脚本
│   ├── mapper_1.py
│   ├── reducer_1.py
│   ├── mapper_2.py
│   └── reducer_2.py
├── scripts/            # 工具脚本
│   ├── generate_data.py # 数据生成器
│   └── export_logs.py   # 将数据库日志导出为文件
├── sql/                # SQL 文件
│   ├── schema.sql      # 数据库模式（建表）
│   ├── data.sql        # 生成的数据 (generate_data.py 的输出)
│   └── queries.sql     # 要求的 SQL 查询语句
└── README.md
```

## 3. 环境设置与安装

### 3.1 前置要求
*   Python 3.8+
*   MySQL 8.0+
*   Hadoop 3.3+ (用于 MapReduce 任务)

### 3.2 Python 依赖
```bash
pip install flask pymysql faker
```

### 3.3 数据库设置
1.  创建数据库和表：
    ```bash
    mysql -u root -p < sql/schema.sql
    ```
2.  生成模拟数据：
    ```bash
    python3 scripts/generate_data.py
    ```
    这将创建 `sql/data.sql` 文件。
3.  导入数据：
    ```bash
    mysql -u root -p smart_campus < sql/data.sql
    ```

## 4. 运行 Web 应用程序
1.  编辑 `app/app.py`，并在 `db_config` 字典中更新你的 MySQL 密码。
2.  运行应用：
    ```bash
    python3 app/app.py
    ```
3.  在浏览器中打开 `http://localhost:5000`。
    *   **管理员登录**: 用户名 `admin`, 密码 `admin123`
    *   **学生登录**: 用户名 `stu0`, 密码 `123456`
    *   **教职工登录**: 用户名 `fac0`, 密码 `123456`

## 5. 运行 MapReduce 任务

### 5.1 准备数据
从 MySQL 导出日志到文本文件：
```bash
python3 scripts/export_logs.py
# 将生成 access.log
```

### 5.2 运行 Hadoop Streaming
请确保 Hadoop 正在运行 (`start-dfs.sh`, `start-yarn.sh`)。

**任务 1: 统计操作次数**
```bash
hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
    -input /input/access.log \
    -output /output/task1 \
    -mapper "python3 $(pwd)/mapreduce/mapper_1.py" \
    -reducer "python3 $(pwd)/mapreduce/reducer_1.py" \
    -file $(pwd)/mapreduce/mapper_1.py \
    -file $(pwd)/mapreduce/reducer_1.py
```

**任务 2: 用户统计 (Top 10)**
```bash
hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
    -input /input/access.log \
    -output /output/task2_raw \
    -mapper "python3 $(pwd)/mapreduce/mapper_2.py" \
    -reducer "python3 $(pwd)/mapreduce/reducer_2.py" \
    -file $(pwd)/mapreduce/mapper_2.py \
    -file $(pwd)/mapreduce/reducer_2.py

# 获取前 10 名 (对结果进行本地处理)
hdfs dfs -cat /output/task2_raw/* | sort -nr | head -n 10
```

## 6. SQL 查询
作业所要求的复杂 SQL 查询位于 `sql/queries.sql` 中。你可以直接在 SQL 客户端中运行它们，或者通过 Web 应用中的“管理员仪表板 (Admin Dashboard)”查看结果。