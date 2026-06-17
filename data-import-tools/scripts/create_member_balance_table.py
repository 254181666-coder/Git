#!/usr/bin/env python3
import pymysql
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS member_balance_change (
    id INT AUTO_INCREMENT PRIMARY KEY,
    member_id VARCHAR(50) DEFAULT '',
    member_name VARCHAR(100) DEFAULT '',
    member_phone VARCHAR(20) DEFAULT '',
    member_level VARCHAR(50) DEFAULT '',
    card_store VARCHAR(100) DEFAULT '',
    change_store VARCHAR(100) DEFAULT '',
    change_type VARCHAR(50) DEFAULT '',
    principal_change DECIMAL(12,2) DEFAULT 0,
    principal_balance DECIMAL(12,2) DEFAULT 0,
    gift_change DECIMAL(12,2) DEFAULT 0,
    gift_balance DECIMAL(12,2) DEFAULT 0,
    room_no VARCHAR(50) DEFAULT '',
    remark VARCHAR(200) DEFAULT '',
    change_time DATETIME DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_member_phone (member_phone),
    INDEX idx_change_time (change_time),
    INDEX idx_change_type (change_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
''')
conn.commit()
print('member_balance_change 表创建成功')

cursor.close()
conn.close()
