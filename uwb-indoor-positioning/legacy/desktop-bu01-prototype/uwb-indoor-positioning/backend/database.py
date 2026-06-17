# 数据库操作 - UWB定位系统（KTV场景完整版）

import pymysql
from datetime import datetime, timedelta
from config import DB_CONFIG


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        charset=DB_CONFIG['charset']
    )


def init_db():
    """初始化数据库，创建所有表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 位置记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                tag_id INT NOT NULL,
                tag_type ENUM('person', 'item') NOT NULL DEFAULT 'person',
                x FLOAT NOT NULL,
                y FLOAT NOT NULL,
                z FLOAT DEFAULT 0,
                room_no VARCHAR(20),
                confidence FLOAT DEFAULT 0,
                anchor_count INT DEFAULT 0,
                timestamp DATETIME NOT NULL,
                INDEX idx_tag_id (tag_id),
                INDEX idx_tag_type (tag_type),
                INDEX idx_timestamp (timestamp),
                INDEX idx_room_no (room_no),
                INDEX idx_tag_time (tag_id, timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # 2. 标签管理表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INT PRIMARY KEY AUTO_INCREMENT,
                tag_no VARCHAR(50) UNIQUE NOT NULL,
                tag_type ENUM('person', 'item') NOT NULL,
                bind_id INT,
                bind_name VARCHAR(100),
                status ENUM('active', 'inactive', 'lost') DEFAULT 'active',
                last_seen DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_status (status),
                INDEX idx_bind_id (bind_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # 3. 包厢/区域表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                id INT PRIMARY KEY AUTO_INCREMENT,
                room_no VARCHAR(20) UNIQUE NOT NULL,
                x_min FLOAT NOT NULL,
                y_min FLOAT NOT NULL,
                x_max FLOAT NOT NULL,
                y_max FLOAT NOT NULL,
                type ENUM('普通', '豪华', 'VIP', '公共') DEFAULT '普通',
                capacity INT DEFAULT 0,
                status ENUM('empty', 'occupied', 'cleaning', 'maintenance') DEFAULT 'empty',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_room_no (room_no),
                INDEX idx_type (type),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # 4. 事件记录表（业务系统对接）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                event_type ENUM('room_open', 'room_close', 'service_remind', 
                               'cleaning_required', 'tool_checkout', 'tool_checkin',
                               'staff_enter', 'staff_leave') NOT NULL,
                source_system VARCHAR(50) DEFAULT 'business',
                reference_id VARCHAR(100),  -- 业务系统订单号等
                room_no VARCHAR(20),
                target_id INT,             -- 目标标签ID或人员ID
                data JSON,                 -- 额外数据
                status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
                triggered_at DATETIME,      -- 触发时间
                processed_at DATETIME,     -- 处理时间
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_event_type (event_type),
                INDEX idx_status (status),
                INDEX idx_room_no (room_no),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # 5. 服务任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_tasks (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                event_id BIGINT,
                task_type ENUM('service', 'cleaning', 'delivery', 'other') NOT NULL,
                room_no VARCHAR(20) NOT NULL,
                assignee_id INT,           -- 被分配的人员ID
                assignee_name VARCHAR(100),
                status ENUM('assigned', 'accepted', 'in_progress', 
                           'completed', 'cancelled') DEFAULT 'assigned',
                priority ENUM('low', 'normal', 'high', 'urgent') DEFAULT 'normal',
                assigned_at DATETIME,
                accepted_at DATETIME,
                started_at DATETIME,
                completed_at DATETIME,
                response_time FLOAT,       -- 响应时间（秒）
                duration FLOAT,            -- 任务时长（秒）
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events(id),
                INDEX idx_task_type (task_type),
                INDEX idx_status (status),
                INDEX idx_assignee (assignee_id),
                INDEX idx_room_no (room_no),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # 6. 业务系统订单同步表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_orders (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                order_no VARCHAR(100) UNIQUE NOT NULL,
                room_no VARCHAR(20) NOT NULL,
                customer_phone VARCHAR(20),
                amount DECIMAL(10, 2),
                status ENUM('opened', 'closed', 'cancelled') NOT NULL,
                open_time DATETIME,
                close_time DATETIME,
                service_reminded TINYINT DEFAULT 0,
                cleaning_assigned TINYINT DEFAULT 0,
                sync_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                raw_data JSON,              -- 原始业务数据
                INDEX idx_order_no (order_no),
                INDEX idx_room_no (room_no),
                INDEX idx_status (status),
                INDEX idx_sync_time (sync_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # 7. 系统日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                log_level ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR') NOT NULL,
                module VARCHAR(50),
                message TEXT,
                details JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_log_level (log_level),
                INDEX idx_module (module),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        conn.commit()
        print("[成功] 数据库初始化完成")
        
    except Exception as e:
        print(f"[错误] 数据库初始化失败: {e}")
        conn.rollback()
    finally:
        conn.close()


# ========== 位置数据操作 ==========

def insert_position(tag_id, x, y, z=None, tag_type='person', room_no=None, confidence=None, anchor_count=None):
    """插入一条位置记录"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        cursor.execute(
            '''INSERT INTO positions 
               (tag_id, tag_type, x, y, z, room_no, confidence, anchor_count, timestamp) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (tag_id, tag_type, x, y, z, room_no, confidence, anchor_count, timestamp)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"插入位置记录失败: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def get_history(tag_id, start_time=None, end_time=None, limit=100):
    """获取历史轨迹"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        query = '''SELECT x, y, room_no, confidence, timestamp 
                   FROM positions WHERE tag_id = %s'''
        params = [tag_id]
        
        if start_time and end_time:
            query += ' AND timestamp BETWEEN %s AND %s'
            params.extend([start_time, end_time])
        
        query += ' ORDER BY timestamp DESC LIMIT %s'
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        return [{
            "x": r[0], "y": r[1], "room_no": r[2],
            "confidence": float(r[3]) if r[3] else None,
            "timestamp": str(r[4])
        } for r in results]
    except Exception as e:
        print(f"获取历史轨迹失败: {e}")
        return []
    finally:
        conn.close()


def get_latest(tag_id, limit=1):
    """获取最新位置"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            '''SELECT x, y, room_no, confidence, timestamp 
               FROM positions WHERE tag_id = %s ORDER BY id DESC LIMIT %s''',
            (tag_id, limit)
        )
        
        results = cursor.fetchall()
        
        if results:
            return {
                "x": results[0][0],
                "y": results[0][1],
                "room_no": results[0][2],
                "confidence": float(results[0][3]) if results[0][3] else None,
                "timestamp": str(results[0][4])
            }
        return None
    except Exception as e:
        print(f"获取最新位置失败: {e}")
        return None
    finally:
        conn.close()


# ========== 标签管理 ==========

def get_all_tags(status=None):
    """获取所有标签"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        query = 'SELECT id, tag_no, tag_type, bind_id, bind_name, status, last_seen FROM tags'
        params = []
        
        if status:
            query += ' WHERE status = %s'
            params.append(status)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        return [{
            "id": r[0], "tag_no": r[1], "tag_type": r[2],
            "bind_id": r[3], "bind_name": r[4],
            "status": r[5], "last_seen": str(r[6]) if r[6] else None
        } for r in results]
    except Exception as e:
        print(f"获取标签列表失败: {e}")
        return []
    finally:
        conn.close()


def add_tag(tag_no, tag_type='person', bind_id=None, bind_name=None):
    """添加标签"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            '''INSERT INTO tags (tag_no, tag_type, bind_id, bind_name) 
               VALUES (%s, %s, %s, %s)''',
            (tag_no, tag_type, bind_id, bind_name)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"添加标签失败: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def update_tag_last_seen(tag_id):
    """更新标签最后在线时间"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            'UPDATE tags SET last_seen = %s WHERE id = %s',
            (now, tag_id)
        )
        conn.commit()
    except Exception as e:
        print(f"更新标签状态失败: {e}")
    finally:
        conn.close()


# ========== 包厢管理 ==========

def get_all_rooms(room_type=None, status=None):
    """获取所有包厢"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        query = 'SELECT id, room_no, x_min, y_min, x_max, y_max, type, capacity, status FROM rooms'
        params = []
        
        conditions = []
        if room_type:
            conditions.append('type = %s')
            params.append(room_type)
        if status:
            conditions.append('status = %s')
            params.append(status)
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        return [{
            "id": r[0], "room_no": r[1],
            "bounds": {"x_min": r[2], "y_min": r[3], "x_max": r[4], "y_max": r[5]},
            "type": r[6], "capacity": r[7], "status": r[8]
        } for r in results]
    except Exception as e:
        print(f"获取包厢列表失败: {e}")
        return []
    finally:
        conn.close()


def add_room(room_no, bounds, room_type='普通', capacity=0):
    """添加包厢"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            '''INSERT INTO rooms (room_no, x_min, y_min, x_max, y_max, type, capacity) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (room_no, bounds.get('x_min'), bounds.get('y_min'),
             bounds.get('x_max'), bounds.get('y_max'),
             room_type, capacity)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"添加包厢失败: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


# ========== 事件管理 ==========

def create_event(event_type, room_no=None, target_id=None, reference_id=None, data=None, trigger_time=None):
    """创建事件"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            '''INSERT INTO events (event_type, room_no, target_id, reference_id, data, triggered_at) 
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (event_type, room_no, target_id, reference_id,
             json.dumps(data) if data else None, trigger_time or datetime.now())
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"创建事件失败: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def get_pending_events(event_type=None, limit=10):
    """获取待处理的事件"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        query = '''SELECT * FROM events WHERE status = 'pending' '''
        params = []
        
        if event_type:
            query += 'AND event_type = %s '
            params.append(event_type)
        
        query += 'ORDER BY created_at ASC LIMIT %s'
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # 返回字典格式
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        print(f"获取待处理事件失败: {e}")
        return []
    finally:
        conn.close()


def update_event_status(event_id, status):
    """更新事件状态"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        now = datetime.now()
        update_fields = ['status = %s']
        params = [status]
        
        if status == 'processing':
            update_fields.append('processed_at = %s')
            params.append(now)
        elif status == 'completed':
            update_fields.append('processed_at = %s')
            params.append(now)
        
        query = f'UPDATE events SET {", ".join(update_fields)} WHERE id = %s'
        params.append(event_id)
        
        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        print(f"更新事件状态失败: {e}")
        conn.rollback()
    finally:
        conn.close()


# ========== 服务任务管理 ==========

def create_task(event_id, task_type, room_no, assignee_id=None, priority='normal'):
    """创建服务任务"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        now = datetime.now()
        cursor.execute(
            '''INSERT INTO service_tasks (event_id, task_type, room_no, assignee_id, priority, assigned_at) 
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (event_id, task_type, room_no, assignee_id, priority, now)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"创建服务任务失败: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def update_task_status(task_id, status, notes=None):
    """更新任务状态"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        now = datetime.now()
        update_fields = ['status = %s']
        params = [status]
        
        if status == 'accepted':
            update_fields.append('accepted_at = %s')
            params.append(now)
        elif status == 'in_progress':
            update_fields.append('started_at = %s')
            params.append(now)
        elif status == 'completed':
            update_fields.append('completed_at = %s')
            params.append(now)
            
            # 计算响应时间和时长
            cursor.execute(
                'SELECT assigned_at, started_at FROM service_tasks WHERE id = %s',
                (task_id,)
            )
            result = cursor.fetchone()
            if result and result[0]:
                response_time = (now - result[0]).total_seconds()
                update_fields.append('response_time = %s')
                params.append(response_time)
                
                if result[1]:
                    duration = (now - result[1]).total_seconds()
                    update_fields.append('duration = %s')
                    params.append(duration)
        
        if notes:
            update_fields.append('notes = %s')
            params.append(notes)
        
        update_fields.append('updated_at = %s')
        params.append(now)
        
        query = f'UPDATE service_tasks SET {", ".join(update_fields)} WHERE id = %s'
        params.append(task_id)
        
        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        print(f"更新任务状态失败: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_tasks_by_room(room_no, status=None, limit=10):
    """按包房查询任务"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        query = '''SELECT * FROM service_tasks WHERE room_no = %s'''
        params = [room_no]
        
        if status:
            query += ' AND status = %s'
            params.append(status)
        
        query += ' ORDER BY created_at DESC LIMIT %s'
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        print(f"查询任务失败: {e}")
        return []
    finally:
        conn.close()


# ========== 数据分析查询 ==========

def get_analytics_overview():
    """获取系统概览数据"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        overview = {}
        
        # 在线标签数（最近5分钟有位置数据的）
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        cursor.execute(
            'SELECT COUNT(DISTINCT tag_id) FROM positions WHERE timestamp > %s',
            (five_minutes_ago,)
        )
        overview['online_tags'] = cursor.fetchone()[0]
        
        # 今日位置记录数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cursor.execute(
            'SELECT COUNT(*) FROM positions WHERE timestamp > %s',
            (today_start,)
        )
        overview['today_positions'] = cursor.fetchone()[0]
        
        # 待处理事件数
        cursor.execute(
            "SELECT COUNT(*) FROM events WHERE status = 'pending'"
        )
        overview['pending_events'] = cursor.fetchone()[0]
        
        # 进行中任务数
        cursor.execute(
            "SELECT COUNT(*) FROM service_tasks WHERE status IN ('assigned', 'in_progress')"
        )
        overview['active_tasks'] = cursor.fetchone()[0]
        
        # 平均响应时间（最近24小时）
        yesterday = datetime.now() - timedelta(hours=24)
        cursor.execute(
            'SELECT AVG(response_time) FROM service_tasks WHERE completed_at > %s AND response_time IS NOT NULL',
            (yesterday,)
        )
        result = cursor.fetchone()[0]
        overview['avg_response_time'] = round(result, 2) if result else None
        
        # 任务完成率（最近7天）
        week_ago = datetime.now() - timedelta(days=7)
        cursor.execute(
            '''SELECT 
                COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*)
               FROM service_tasks 
               WHERE created_at > %s''',
            (week_ago,)
        )
        result = cursor.fetchone()[0]
        overview['task_completion_rate'] = round(result, 2) if result else None
        
        return overview
    except Exception as e:
        print(f"获取分析数据失败: {e}")
        return {}
    finally:
        conn.close()


def get_efficiency_report(period='week'):
    """获取效率报表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 计算时间范围
        if period == 'day':
            start_time = datetime.now() - timedelta(days=1)
        elif period == 'week':
            start_time = datetime.now() - timedelta(weeks=1)
        elif period == 'month':
            start_time = datetime.now() - timedelta(days=30)
        else:
            start_time = datetime.now() - timedelta(weeks=1)
        
        report = {
            'period': period,
            'start_time': str(start_time),
            'end_time': str(datetime.now())
        }
        
        # 各类型任务统计
        cursor.execute(
            '''SELECT task_type, 
                      COUNT(*) as total,
                      SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                      AVG(response_time) as avg_response,
                      AVG(duration) as avg_duration
               FROM service_tasks 
               WHERE created_at > %s
               GROUP BY task_type''',
            (start_time,)
        )
        
        report['by_type'] = []
        for row in cursor.fetchall():
            report['by_type'].append({
                'task_type': row[0],
                'total': row[1],
                'completed': row[2],
                'avg_response_time': round(row[3], 2) if row[3] else None,
                'avg_duration': round(row[4], 2) if row[4] else None
            })
        
        # 高峰时段统计
        cursor.execute(
            '''SELECT HOUR(created_at) as hour, COUNT(*) as count
               FROM service_tasks 
               WHERE created_at > %s
               GROUP BY HOUR(created_at)
               ORDER BY count DESC
               LIMIT 5''',
            (start_time,)
        )
        
        report['peak_hours'] = [f"{row[0]}:00-{row[0]}+1:00 ({row[1]}个任务)" for row in cursor.fetchall()]
        
        # 表现最好的员工（完成任务最多且响应最快）
        cursor.execute(
            '''SELECT assignee_id, assignee_name, 
                      COUNT(*) as tasks_completed,
                      AVG(response_time) as avg_response_time
               FROM service_tasks 
               WHERE created_at > %s AND status = 'completed' AND assignee_id IS NOT NULL
               GROUP BY assignee_id, assignee_name
               ORDER BY tasks_completed DESC, avg_response_time ASC
               LIMIT 10''',
            (start_time,)
        )
        
        report['top_performers'] = []
        for row in cursor.fetchall():
            report['top_performers'].append({
                'id': row[0],
                'name': row[1],
                'tasks_completed': row[2],
                'avg_response_time': round(row[3], 2) if row[3] else None
            })
        
        return report
    except Exception as e:
        print(f"获取效率报表失败: {e}")
        return {}
    finally:
        conn.close()


# ========== 日志记录 ==========

def log(level, module, message, details=None):
    """记录系统日志"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            '''INSERT INTO system_logs (log_level, module, message, details) 
               VALUES (%s, %s, %s, %s)''',
            (level, module, message, json.dumps(details) if details else None)
        )
        conn.commit()
    except Exception as e:
        print(f"写入日志失败: {e}")
    finally:
        conn.close()
