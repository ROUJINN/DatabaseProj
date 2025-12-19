CREATE DATABASE IF NOT EXISTS smart_campus;
USE smart_campus;

CREATE TABLE IF NOT EXISTS Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
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

CREATE INDEX idx_trans_time ON Transactions(time);
CREATE INDEX idx_trans_card ON Transactions(card_id);
CREATE INDEX idx_student_dept ON Students(department);
CREATE INDEX idx_access_time ON AccessLogs(time);

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
