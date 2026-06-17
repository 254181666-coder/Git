"""
数据库操作统一封装
支持 MySQL 和 SQLite，通过 src/config.py 中的 USE_MYSQL 开关切换
性能优化：
- 充分利用 SQLAlchemy 连接池
- 减少不必要的连接创建/关闭
- 统一参数化查询接口
"""
import pandas as pd
from pathlib import Path
from typing import List, Any, Optional
from .config import DB_PATH, USE_MYSQL, MYSQL_CONFIG


_engine = None

def get_engine():
    """获取数据库引擎（单例模式）"""
    global _engine
    if _engine is not None:
        return _engine
    if USE_MYSQL:
        from sqlalchemy import create_engine, pool, text
        user = MYSQL_CONFIG['user']
        password = MYSQL_CONFIG['password']
        host = MYSQL_CONFIG['host']
        port = MYSQL_CONFIG['port']
        database = MYSQL_CONFIG['database']
        charset = MYSQL_CONFIG.get('charset', 'utf8mb4')
        _engine = create_engine(
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}",
            poolclass=pool.QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )
    else:
        from sqlalchemy import create_engine
        _engine = create_engine(f"sqlite:///{DB_PATH}")
    return _engine


def _convert_params_for_mysql(params):
    """将 SQLite 风格的 ? 参数转换为 MySQL 风格的 %s 参数"""
    if params is None:
        return None, None
    if USE_MYSQL:
        sql_params = {}
        converted_sql_parts = []
        param_idx = 0
        params_list = list(params) if isinstance(params, (list, tuple)) else [params]
        
        for part in params_list:
            param_name = f'param_{param_idx}'
            sql_params[param_name] = part
            param_idx += 1
        return sql_params, param_idx
    return params, None


def query(sql: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
    """高性能查询：使用 SQLAlchemy 连接池
    
    Args:
        sql: SQL 查询语句（使用 ? 作为占位符）
        params: 参数列表
        
    Returns:
        查询结果 DataFrame
    """
    engine = get_engine()
    from sqlalchemy import text
    
    try:
        if USE_MYSQL:
            # MySQL 参数替换
            sql_with_named_params = sql
            if params is not None:
                param_list = list(params) if isinstance(params, (list, tuple)) else [params]
                for i in range(len(param_list)):
                    sql_with_named_params = sql_with_named_params.replace('?', f':param_{i}', 1)
                
                sql_params = {f'param_{i}': val for i, val in enumerate(param_list)}
            else:
                sql_params = {}
            
            with engine.connect() as conn:
                result = conn.execute(text(sql_with_named_params), sql_params)
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df
        else:
            # SQLite 直接使用原生方式
            return pd.read_sql_query(sql, engine, params=params)
    except Exception as e:
        print(f"Query error: {e}")
        return pd.DataFrame()


def execute(sql: str, params: Optional[List[Any]] = None) -> None:
    """高性能执行：使用连接池
    
    Args:
        sql: SQL 语句（使用 ? 作为占位符）
        params: 参数列表
    """
    engine = get_engine()
    from sqlalchemy import text
    
    with engine.begin() as conn:
        if USE_MYSQL:
            sql_with_named_params = sql
            sql_params = {}
            if params is not None:
                param_list = list(params) if isinstance(params, (list, tuple)) else [params]
                for i in range(len(param_list)):
                    sql_with_named_params = sql_with_named_params.replace('?', f':param_{i}', 1)
                sql_params = {f'param_{i}': val for i, val in enumerate(param_list)}
            
            conn.execute(text(sql_with_named_params), sql_params)
        else:
            conn.execute(text(sql), params or ())


def execute_many(sql: str, params_list: List[List[Any]]) -> None:
    """高性能批量执行：使用连接池
    
    Args:
        sql: SQL 语句（使用 ? 作为占位符）
        params_list: 参数列表的列表
    """
    engine = get_engine()
    from sqlalchemy import text
    
    with engine.begin() as conn:
        if USE_MYSQL:
            for params in params_list:
                sql_with_named_params = sql
                sql_params = {}
                if params is not None:
                    param_list = list(params) if isinstance(params, (list, tuple)) else [params]
                    for i in range(len(param_list)):
                        sql_with_named_params = sql_with_named_params.replace('?', f':param_{i}', 1)
                    sql_params = {f'param_{i}': val for i, val in enumerate(param_list)}
                
                conn.execute(text(sql_with_named_params), sql_params)
        else:
            for params in params_list:
                conn.execute(text(sql), params or ())


def backup_database(backup_path: Path = None) -> Path:
    if backup_path is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = DB_PATH.parent / "backups" / f"ktv_analysis_{timestamp}.db"
    import shutil
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, backup_path)
    return backup_path
