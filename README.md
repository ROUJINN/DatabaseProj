使用的数据通过
python scripts/generate_data.py
来生成，生成的结果见 sql/data.sql

SQL程序见 sql/queries.sql 和 sql/schema.sql

用户程序代码见 app/

小组分工情况：
罗骏完成选择技术栈，代码框架的搭建，数据库设计，实现大多基本功能，mapreduce部分，readme的撰写，演示
蔡浩楠完成细节的feature，包括
admin: manage 用户,校园卡,商户终端,门禁系统(门禁点&门禁权限)[add/delete/edit],处理faculty修改card的request
student: 个人信息展示完善，查询所有的消费记录、门禁记录，模拟消费，充值，系统自动显示当日累计消费和账户余额
faculty: 导出所管理学生的消费记录、门禁记录，向管理员请求修改学生卡的状态，查询所有的消费记录、门禁记录
周一帆完成ER图，关系模式表，优化程序代码
给分占比：平均给分

---

报告中的问题
以上哪个查询耗时最长？请给出相应的优化查询的手段（比如创建索引等），并分析通过这样的手段如何提升了查询性能。

由于缓存机制的存在，对每个query，第一次查询耗的时间要显著大于之后查询耗的时间，我们列出除第一次外的5次查询的性能

| 状态/查询编号 | 时间1/ms | 时间2/ms | 时间3/ms | 时间4/ms | 时间5/ms | 平均时间/ms |
|---------------|----------|----------|----------|----------|----------|-------------|
| 1A            | 6        | 3        | 2        | 2        | 1        | 2.80        |
| 1B            | 5        | 6        | 3        | 1        | 2        | 3.40        |
| 2             | 5        | 4        | 3        | 4        | 4        | 4.00        |
| 3             | 3        | 4        | 3        | 4        | 4        | 3.60        |
| 4             | 2        | 8        | 2        | 2        | 3        | 3.40        |
| 5             | 3        | 4        | 3        | 3        | 4        | 3.40        |
| 6（原）       | 11       | 5        | 4        | 5        | 5        | 6.00        |
| 7             | 2        | 2        | 2        | 2        | 1        | 1.80        |
| 6（加index后）| 5        | 5        | 4        | 5        | 4        | 4.60        |

6查询耗时最长，优化的手段是
CREATE INDEX idx_trans_time ON Transactions(time);
优化了其中的GROUP BY DATE(t.time)的操作

---
如何运行程序？

安装mysql  
sudo apt install mysql-server -y  
启动 MySQL 服务  
sudo service mysql start  

安装Python包  
pip install flask pymysql faker  

初始化mysql
sudo mysql  
source sql/schema.sql;  
修改 MySQL 密码以便 Python 连接  
为了让 app.py 能连上数据库，我们需要设置 root 用户的密码（假设设为123456）：  
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';  
FLUSH PRIVILEGES;  
EXIT;  

生成数据  
python scripts/generate_data.py  
这会在 sql/ 目录下生成 data.sql。  

导入数据将生成的数据导入 MySQL（此时需要输入刚才设置的密码 123456）：  
mysql -u root -p < sql/data.sql
这一步实际配置时，如果在用conda，Conda 环境里自带了一个 mysql 客户端，它的默认配置路径（/tmp/...）和 Ubuntu 系统自带的 MySQL 服务路径（/var/run/...）不一致。可以强制通过 IP 连接，不要用 socket 文件连接，而是强制通过 TCP/IP 网络连接来解决。加上 -h 127.0.0.1 参数：  
mysql -u root -p -h 127.0.0.1 < sql/data.sql  

配置并运行 Web 应用  

修改配置文件：  
你需要编辑 app/app.py。  
找到 db_config 部分，把 password 改成你在第二步里设置的密码（例如 '123456'）。  
运行应用：  
python app/app.py  
访问网页：  
在 Windows 的浏览器中输入：http://localhost:5000。WSL2 会自动把端口转发出来。  
使用管理员账号登录测试：admin / admin123
学生账号：stu{i} / 123456 其中i是从1到NUM_STUDENTS = 40的任意一个数
教师账号：fac{i} / 123456 其中i是从1到NUM_FACULTY = 20的任意一个数

Hadoop安装  单机模式 (Standalone Mode) 
安装 Java (必装)  
sudo apt update  
sudo apt install openjdk-8-jdk -y  
下载并解压 Hadoop  
直接复制粘贴运行（下载到当前目录）：  
wget https://mirrors.tuna.tsinghua.edu.cn/apache/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz  
tar -zxvf hadoop-3.3.6.tar.gz  
mv hadoop-3.3.6 hadoop  
我用的是/home/roujin/Python/hadoop  
第三步：告诉 Hadoop Java 在哪
运行这行命令，直接把配置写入文件
echo "export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64" >> /home/roujin/Python/hadoop/etc/hadoop/hadoop-env.sh  
第四步：
从 MySQL 导出日志到文本文件：  
python scripts/export_logs.py  
假设你已经在项目根目录，且生成了 access.log。  
运行hadoop
source run.sh
结果在output_task1和output_task2里

