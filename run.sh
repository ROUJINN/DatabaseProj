HADOOP_BIN="/home/roujin/Python/hadoop/bin/hadoop"
STREAMING_JAR="/home/roujin/Python/hadoop/share/hadoop/tools/lib/hadoop-streaming-*.jar"

# Ensure access.log exists
if [ ! -f "access.log" ]; then
    echo "access.log not found. Generating..."
    python3 scripts/export_logs.py
fi

# Task 1
echo "========================================================"
echo "Running Task 1: Access Operations Count"
echo "========================================================"
rm -rf output_task1
$HADOOP_BIN jar $STREAMING_JAR \
    -input access.log \
    -output output_task1 \
    -mapper "python3 mapper1.py" \
    -reducer "python3 reducer1.py" \
    -file mapreduce/mapper1.py \
    -file mapreduce/reducer1.py

echo ""
echo "Task 1 Results:"
if [ -d "output_task1" ]; then
    cat output_task1/part-*
else
    echo "Task 1 output directory not found."
fi

# Task 2
echo ""
echo "========================================================"
echo "Running Task 2: Top 10 Users by Operation Count"
echo "========================================================"
rm -rf output_task2
$HADOOP_BIN jar $STREAMING_JAR \
    -input access.log \
    -output output_task2 \
    -mapper "python3 mapper2.py" \
    -reducer "python3 reducer2.py" \
    -file mapreduce/mapper2.py \
    -file mapreduce/reducer2.py

echo ""
echo "Task 2 Results:"
if [ -d "output_task2" ]; then
    cat output_task2/part-*
else
    echo "Task 2 output directory not found."
fi

# 删除复制过来的临时文件
rm mapper1.py reducer1.py mapper2.py reducer2.py