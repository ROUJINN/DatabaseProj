/home/roujin/Python/hadoop/bin/hadoop jar /home/roujin/Python/hadoop/share/hadoop/tools/lib/hadoop-streaming-*.jar \
    -input access.log \
    -output output_task1 \
    -mapper "python3 mapreduce/mapper_1.py" \
    -reducer "python3 mapreduce/reducer_1.py" \
    -file mapreduce/mapper_1.py \
    -file mapreduce/reducer_1.py