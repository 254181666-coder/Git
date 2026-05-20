"""
数据库连接模块
"""
import sqlite3

from src.config import DB_PATH

def get_connection():
    """获取SQLite连接"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _sqlite_sql(sql):
    """兼容旧MySQL脚本里的%s占位符。"""
    return sql.replace("%s", "?")

def query(sql, params=None):
    """执行查询并返回DataFrame"""
    import pandas as pd
    conn = get_connection()
    try:
        df = pd.read_sql_query(_sqlite_sql(sql), conn, params=params)
        return df
    finally:
        conn.close()

def execute(sql, params=None):
    """执行SQL语句"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(_sqlite_sql(sql), params or ())
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
