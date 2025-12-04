安装mysql  
sudo apt install mysql-server -y  
启动 MySQL 服务  
sudo service mysql start  

安装Python包  
pip3 install flask pymysql faker  

初始化mysql  
sudo mysql  
source sql/schema.sql;  
修改 MySQL 密码以便 Python 连接  
为了让 `app.py` 能连上数据库，我们需要设置 root 用户的密码（假设设为 `123456`，请根据你自己想设的改）：  

ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';  
FLUSH PRIVILEGES;  
EXIT;  

生成数据  
python3 scripts/generate_data.py  
这会在 `sql/` 目录下生成 `data.sql`。  

导入数据将生成的数据导入 MySQL（此时需要输入刚才设置的密码 `123456`）：  
mysql -u root -p < sql/data.sql  

这一步实际配置时，如果在用conda，Conda 环境里自带了一个 mysql 客户端，它的默认配置路径（/tmp/...）和 Ubuntu 系统自带的 MySQL 服务路径（/var/run/...）不一致。可以强制通过 IP 连接，不要用 socket 文件连接，而是强制通过 TCP/IP 网络连接来解决。加上 -h 127.0.0.1 参数：  
mysql -u root -p -h 127.0.0.1 < sql/data.sql  

配置并运行 Web 应用  

1. 修改配置文件：  
你需要编辑 `app/app.py`。  

找到 `db_config` 部分，把 `password` 改成你在第二步里设置的密码（例如 `'123456'`）。  

2. 运行应用：  
python3 app/app.py  

3. 访问网页：  
* 在 Windows 的浏览器中输入：`http://localhost:5000`。WSL2 会自动把端口转发出来。  
* 使用管理员账号登录测试：`admin` / `admin123`。  

Hadoop安装  

既然你要最简单的，那就选 “单机模式 (Standalone Mode)”。   

第一步：安装 Java (必装)  

打开 WSL 终端，复制粘贴运行：  
sudo apt update  
sudo apt install openjdk-8-jdk -y  

第二步：下载并解压 Hadoop  

直接复制粘贴运行（下载到当前目录）：  
wget https://mirrors.tuna.tsinghua.edu.cn/apache/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz  
tar -zxvf hadoop-3.3.6.tar.gz  
mv hadoop-3.3.6 hadoop  

我用的是/home/roujin/Python/hadoop  

第三步：告诉 Hadoop Java 在哪 (唯一需要改的配置)  

运行这行命令，直接把配置写入文件（免去你打开编辑器找位置的麻烦）：  
echo "export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64" >> /home/roujin/Python/hadoop/etc/hadoop/hadoop-env.sh  

第四步：怎么运行你的项目？  

从 MySQL 导出日志到文本文件：  
python3 scripts/export_logs.py  

假设你已经在项目根目录，且生成了 `access.log`。  

任务 1 的运行命令（修改版）：  
*(注意：我把输入输出路径改成了本地路径，请直接复制)*  

/home/roujin/Python/hadoop/bin/hadoop jar /home/roujin/Python/hadoop/share/hadoop/tools/lib/hadoop-streaming-*.jar \  
-input access.log \  
-output output_task1 \  
-mapper "python3 mapreduce/mapper_1.py" \  
-reducer "python3 mapreduce/reducer_1.py" \  
-file mapreduce/mapper_1.py \  
-file mapreduce/reducer_1.py  

运行成功后查看结果：  
cat output_task1/part-00000  
