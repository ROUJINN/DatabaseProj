-- 1. 查找学生“王X明”在2025年12月21日（含）之前的消费总额，并给出其最近一次到达的门禁点信息
-- Part A: Consumption Total
SELECT 
    s.name, 
    SUM(t.amount) as total_consumption
FROM Students s
JOIN Cards c ON s.user_id = c.user_id
JOIN Transactions t ON c.card_id = t.card_id
WHERE s.name LIKE '王_明%' 
  AND CHAR_LENGTH(s.name) >= 3
  AND t.time <= '2025-12-21 23:59:59'
GROUP BY s.student_id;

-- Part B: Last Access Point
SELECT 
    s.name, 
    ap.building_name, 
    al.time
FROM Students s
JOIN Cards c ON s.user_id = c.user_id
JOIN AccessLogs al ON c.card_id = al.card_id
JOIN AccessPoints ap ON al.point_id = ap.point_id
WHERE s.name LIKE '王_明%' 
  AND CHAR_LENGTH(s.name) >= 3
ORDER BY al.time DESC
LIMIT 1;


-- 2. 查找平均单笔消费金额低于全体人员总体平均单笔消费金额的人员信息，并按照其平均单笔消费金额降序排序
WITH GlobalAvg AS (
    SELECT AVG(amount) as avg_amt FROM Transactions WHERE trans_type = 'payment'
),
UserAvg AS (
    SELECT 
        u.user_id,
        AVG(t.amount) as user_avg_amt
    FROM Users u
    JOIN Cards c ON u.user_id = c.user_id
    JOIN Transactions t ON c.card_id = t.card_id
    WHERE t.trans_type = 'payment'
    GROUP BY u.user_id
)
SELECT 
    u.username,
    ua.user_avg_amt
FROM UserAvg ua
JOIN Users u ON ua.user_id = u.user_id
JOIN GlobalAvg ga
WHERE ua.user_avg_amt < ga.avg_amt
ORDER BY ua.user_avg_amt DESC;


-- 3. 找出2025年12月15日（含）之后消费金额前十的人员，展示其姓名和电话号码，按照消费次数进行降序排序。
-- 若次数相同，则按照顾客姓名字母次序升序排序
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
LIMIT 10; 

-- 4. 查询2025年12月21日（含）之前最“繁忙”的门禁点上的所属管理单位编号以及出入次数。
SELECT 
    ap.manager_dept_id,
    COUNT(*) as access_count
FROM AccessLogs al
JOIN AccessPoints ap ON al.point_id = ap.point_id
WHERE al.time <= '2025-12-21 23:59:59'
GROUP BY ap.point_id
ORDER BY access_count DESC
LIMIT 1;


-- 5. 找出2025年12月14日到19日（含）期间，“智能学院”学生每天的平均消费金额最大的商户名称以及其所有相关交易
-- Step 1: Find the merchant
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
-- Step 2: Get transactions for that merchant (in that date range? or all? Assuming in range)
SELECT t.* 
FROM Transactions t
JOIN DailyMerchantAvg dma ON t.merchant_name = dma.merchant_name
WHERE t.time BETWEEN '2025-12-14 00:00:00' AND '2025-12-19 23:59:59';


-- 6. 查询单日之内消费次数超过“智能学院”平均值两倍（含）的用户姓名、学号/工号与所属单位
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
WHERE uds.user_count >= 2 * sds.avg_daily_count;


-- 7. 查询22:00—06:00期间，“计算机学院”学生在理科二号楼有门禁出入记录的人员
-- 统计夜间出入次数并按次数降序排列，次数相同按姓名拼音升序
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
ORDER BY night_access_count DESC, s.name ASC;
