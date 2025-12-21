CREATE DATABASE IF NOT EXISTS smart_campus;
USE smart_campus;

CREATE TABLE IF NOT EXISTS Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY, 
    -- AUTO_INCREMENT 表示每增加一个新用户，该数字自动加1
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('student', 'faculty', 'admin') NOT NULL
);

CREATE TABLE IF NOT EXISTS Students (
    student_id VARCHAR(20) PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    gender ENUM('M', 'F') NOT NULL,
    identity_card VARCHAR(20) UNIQUE NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    department VARCHAR(50) NOT NULL,
    grade VARCHAR(20),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    -- 外键约束。这表示 Students 表中的 user_id 必须在 Users 表中存在。
    -- ON DELETE CASCADE: 级联删除。如果 Users 表中删除了某个用户，Students 表中对应的记录也会被系统自动删除。
);

CREATE TABLE IF NOT EXISTS Faculty (
    staff_id VARCHAR(20) PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    gender ENUM('M', 'F') NOT NULL,
    identity_card VARCHAR(20) UNIQUE NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    department VARCHAR(50) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Cards (
    card_id VARCHAR(20) PRIMARY KEY,
    user_id INT NOT NULL,
    status ENUM('normal', 'lost', 'frozen') DEFAULT 'normal',
    -- DECIMAL(10, 2)。这表示存储精确数值，总共最多 10 位数字，其中小数点后保留 2 位
    balance DECIMAL(10, 2) DEFAULT 0.00,
    subsidy_balance DECIMAL(10, 2) DEFAULT 0.00,
    open_date DATE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS AccessPoints (
    point_id INT AUTO_INCREMENT PRIMARY KEY,
    building_name VARCHAR(50) NOT NULL,
    manager_dept_id VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS Transactions (
    trans_id INT AUTO_INCREMENT PRIMARY KEY,
    card_id VARCHAR(20) NOT NULL,
    trans_type ENUM('payment', 'recharge') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    merchant_name VARCHAR(50),
    time DATETIME NOT NULL,
    FOREIGN KEY (card_id) REFERENCES Cards(card_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE
    -- ON UPDATE CASCADE: 如果卡号在 Cards 表中被修改，这里也会自动同步修改。
);

CREATE TABLE IF NOT EXISTS Terminals (
    terminal_id VARCHAR(20) PRIMARY KEY,
    merchant_name VARCHAR(50) NOT NULL,
    category VARCHAR(20) DEFAULT 'general',
    charge_rule VARCHAR(100),
    manager_dept VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS AccessRights (
    right_id INT AUTO_INCREMENT PRIMARY KEY,
    role_type ENUM('student','faculty','department') NOT NULL,
    role_value VARCHAR(50) NOT NULL,
    point_id INT NOT NULL,
    FOREIGN KEY (point_id) REFERENCES AccessPoints(point_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS AccessLogs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    card_id VARCHAR(20) NOT NULL,
    point_id INT NOT NULL,
    direction ENUM('in', 'out') NOT NULL,
    time DATETIME NOT NULL,
    FOREIGN KEY (card_id) REFERENCES Cards(card_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (point_id) REFERENCES AccessPoints(point_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS UserMessages (
    msg_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- DEFAULT CURRENT_TIMESTAMP 表示如果插入数据时不指定时间，系统会自动填入当前时间。
    CONSTRAINT fk_user_messages_user
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS CardStatusRequests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    card_id VARCHAR(20) NOT NULL,
    requested_by INT NOT NULL,
    new_status ENUM('normal','lost','frozen') NOT NULL,
    request_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    approved_by INT,
    approved_time DATETIME,
    status ENUM('pending','approved','rejected') DEFAULT 'pending',
    FOREIGN KEY (card_id) REFERENCES Cards(card_id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES Users(user_id) ON DELETE SET NULL
);


-- card_id作为外键，MySQL强制要求必须有索引，同时也不能删除索引。可以如下手动写，如果没写会自动创建
-- CREATE INDEX idx_trans_card ON Transactions(card_id); 

-- 创建索引
CREATE INDEX idx_trans_time ON Transactions(time);


-- 删除索引
-- DROP INDEX idx_trans_time ON Transactions;


-- 在编写触发器时，代码块内部会包含多条以 ; 结束的SQL语句。如果直接执行，数据库解析器会在遇到第一个 ; 时就认为整个命令结束了，从而导致语法错误。
-- DELIMITER // 的作用是将数据库的语句结束符临时修改为 // 
-- 定义完成后，使用 DELIMITER ; 将结束符改回默认的分号
DELIMITER //
CREATE TRIGGER after_transaction_insert
AFTER INSERT ON Transactions
FOR EACH ROW
BEGIN
    DECLARE current_balance DECIMAL(10, 2);
    DECLARE daily_total DECIMAL(10, 2);
    DECLARE uid INT;
    
    IF NEW.trans_type = 'payment' THEN
        SELECT user_id, balance INTO uid, current_balance FROM Cards WHERE card_id = NEW.card_id;
        
        SELECT SUM(amount) INTO daily_total 
        FROM Transactions 
        WHERE card_id = NEW.card_id 
          AND trans_type = 'payment'
          AND DATE(time) = DATE(NEW.time);
          
        INSERT INTO UserMessages (user_id, message) 
        VALUES (uid, CONCAT('Today Total Payment: ', IFNULL(daily_total, 0), ', Current Balance: ', IFNULL(current_balance, 0)));
        
    END IF;
END;
//
DELIMITER ;
