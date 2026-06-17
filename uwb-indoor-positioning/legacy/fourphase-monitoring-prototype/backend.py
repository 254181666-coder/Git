"""
恒迹云UWB MQTT对接 + WebSocket推送后端 + 服务人员到岗监控
依赖: pip install paho-mqtt websockets requests sqlalchemy flask
"""

import json
import os
import asyncio
import hashlib
import random
import threading
import paho.mqtt.client as mqtt
from websockets.server import serve
from websockets.exceptions import ConnectionClosed
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Set, List
import logging
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

global_loop = None
loop_lock = threading.Lock()

def get_event_loop():
    global global_loop
    with loop_lock:
        if global_loop is None:
            try:
                global_loop = asyncio.get_running_loop()
            except RuntimeError:
                global_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(global_loop)
        return global_loop

try:
    from config import *
    logger.info("已加载外部配置文件 config.py")
except ImportError:
    logger.warning("未找到 config.py，使用默认配置")
    MQTT_HOST = "localhost"
    MQTT_PORT = 1883
    MQTT_USERNAME = ""
    MQTT_PASSWORD = ""
    TENANT_ID = 1
    WS_PORT = 8887
    CHECK_DELAY_MINUTES = 30
    NOTIFICATION = {
        "enable": False,
        "feishu_webhook": "",
        "sms_enable": False,
        "admin_notify_phone": "",
    }
    BUSINESS_API = {
        "base_url": "https://open-api.fun360.cn",
        "app_id": "YYP",
        "app_secret": "",
        "enable_polling": False,
    }
    DATABASE_URL = "sqlite:///./uwb_monitoring.db"
    FLASK_HOST = "0.0.0.0"
    FLASK_PORT = 8888

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class MerchantDB(Base):
    __tablename__ = "merchants"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    create_time = Column(DateTime, default=datetime.now)

class AreaDB(Base):
    __tablename__ = "areas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    min_x = Column(Float)
    max_x = Column(Float)
    min_y = Column(Float)
    max_y = Column(Float)
    create_time = Column(DateTime, default=datetime.now)

class StaffDB(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, autoincrement=True)
    card_id = Column(Integer, unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    merchant_id = Column(Integer, nullable=False)
    phone = Column(String(20))
    create_time = Column(DateTime, default=datetime.now)

class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    card_id = Column(Integer, unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    item_type = Column(String(50))
    create_time = Column(DateTime, default=datetime.now)

class ServiceOrderDB(Base):
    __tablename__ = "service_orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(100), unique=True, nullable=False)
    customer_name = Column(String(50), nullable=False)
    room_number = Column(String(50), nullable=False)
    service_area_id = Column(Integer, nullable=False)
    service_area_name = Column(String(100))
    create_time = Column(Integer, nullable=False)
    status = Column(String(20), default="active")
    create_time_dt = Column(DateTime, default=datetime.now)

class ServiceTaskDB(Base):
    __tablename__ = "service_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('service_orders.id'), nullable=False)
    task_id = Column(String(100), nullable=False)
    task_name = Column(String(100), nullable=False)
    assigned_card_id = Column(Integer, nullable=False)
    assigned_name = Column(String(50), nullable=False)
    area_id = Column(Integer, nullable=False)
    area_name = Column(String(100), nullable=False)
    check_delay_minutes = Column(Integer, nullable=False)
    scheduled_check_time = Column(Integer, nullable=False)
    status = Column(String(20), default="pending")
    checked_time = Column(Integer)
    arrived_time = Column(Integer)
    leave_time = Column(Integer)
    duration_minutes = Column(Integer)

class ItemStayRecordDB(Base):
    __tablename__ = "item_stay_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, nullable=False)
    item_name = Column(String(100), nullable=False)
    area_id = Column(Integer, nullable=False)
    area_name = Column(String(100), nullable=False)
    enter_time = Column(Integer, nullable=False)
    leave_time = Column(Integer)
    duration_minutes = Column(Integer)
    create_time_dt = Column(DateTime, default=datetime.now)

Base.metadata.create_all(engine)

TOPICS = [
    (f"/{TENANT_ID}/pos_business/card_now_info/#", 0),
    (f"/{TENANT_ID}/pos_business/inarea", 0),
    (f"/{TENANT_ID}/pos_business/outarea", 0),
    (f"/{TENANT_ID}/alarm/start/#", 0),
    (f"/{TENANT_ID}/alarm/stop/#", 0),
]

@dataclass
class Location:
    card_id: int
    uuid: int
    utype: int
    name: str
    x: float
    y: float
    z: float
    floor_id: int
    floor_name: str
    building_id: int
    building_name: str
    scene_id: int
    scene_name: str
    is_alarm: bool = False
    alarm_info: Optional[str] = None
    timestamp: int = 0

@dataclass
class Alarm:
    id: int
    rule_type: int
    rule_name: str
    level: str
    card_id: Optional[int]
    uuid: Optional[int]
    area_name: Optional[str]
    time: int
    message: str

@dataclass
class ServiceTask:
    task_id: str
    task_name: str
    assigned_card_id: int
    assigned_name: str
    area_id: int
    area_name: str
    check_delay_minutes: int
    scheduled_check_time: int
    area_bounds: Optional[Dict] = None
    status: str = "pending"
    checked_time: Optional[int] = None
    arrived_time: Optional[int] = None
    leave_time: Optional[int] = None
    duration_minutes: Optional[int] = None

@dataclass
class ServiceOrder:
    order_id: str
    customer_name: str
    room_number: str
    service_area_id: int
    service_area_name: str
    create_time: int
    service_area_bounds: Optional[Dict] = None
    status: str = "active"
    tasks: List[ServiceTask] = None
    
    def __post_init__(self):
        if self.tasks is None:
            self.tasks = []

@dataclass
class ItemStayStat:
    item_id: int
    item_name: str
    item_type: str
    current_area_id: Optional[int] = None
    current_area_name: Optional[str] = None
    enter_time: Optional[int] = None
    total_duration_today: int = 0

@dataclass
class StaffStayStat:
    card_id: int
    staff_name: str
    current_area_id: Optional[int] = None
    current_area_name: Optional[str] = None
    enter_time: Optional[int] = None
    total_duration_today: int = 0

connected_clients: Set = set()
locations: Dict[int, Location] = {}
service_orders: Dict[str, ServiceOrder] = {}
staff_stats: Dict[int, StaffStayStat] = {}
item_stats: Dict[int, ItemStayStat] = {}

def verify_sign(app_id: str, app_secret: str, nonce: str, timestamp: str, sign: str) -> bool:
    try:
        params = [f"nonce={nonce}", f"secret={app_secret}", f"timestamp={timestamp}"]
        params_sorted = sorted(params)
        sign_str = "&".join(params_sorted)
        md5_result = hashlib.md5(sign_str.encode('utf-8')).hexdigest().lower()
        return md5_result == sign.lower()
    except Exception as e:
        logger.error(f"签名验证失败: {e}")
        return False

def add_service_order(order: ServiceOrder):
    if order.order_id in service_orders:
        logger.warning(f"订单已存在，跳过: {order.order_id}")
        return
    
    service_orders[order.order_id] = order
    logger.info(f"新增服务订单: {order.order_id} 客户: {order.customer_name} 房间: {order.room_number} 任务数: {len(order.tasks)}")
    
    try:
        session = Session()
        order_db = ServiceOrderDB(
            order_id=order.order_id,
            customer_name=order.customer_name,
            room_number=order.room_number,
            service_area_id=order.service_area_id,
            service_area_name=order.service_area_name,
            create_time=order.create_time,
            status=order.status
        )
        session.add(order_db)
        session.flush()
        
        for task in order.tasks:
            task_db = ServiceTaskDB(
                order_id=order_db.id,
                task_id=task.task_id,
                task_name=task.task_name,
                assigned_card_id=task.assigned_card_id,
                assigned_name=task.assigned_name,
                area_id=task.area_id,
                area_name=task.area_name,
                check_delay_minutes=task.check_delay_minutes,
                scheduled_check_time=task.scheduled_check_time,
                status=task.status,
            )
            session.add(task_db)
        
        session.commit()
    except Exception as e:
        logger.error(f"保存订单失败: {e}")
    finally:
        session.close()
    
    loop = get_event_loop()
    for task in order.tasks:
        asyncio.run_coroutine_threadsafe(delay_check_task(order.order_id, task.task_id), loop)
    
    broadcast({
        "type": "order_created",
        "data": asdict(order)
    })

async def delay_check_task(order_id: str, task_id: str):
    order = service_orders.get(order_id)
    if not order:
        return
    
    task = next((t for t in order.tasks if t.task_id == task_id), None)
    if not task:
        return
    
    wait_seconds = (task.scheduled_check_time / 1000) - time.time()
    if wait_seconds > 0:
        logger.info(f"订单{order_id} 任务{task_id} 将在{wait_seconds:.1f}秒后检查")
        await asyncio.sleep(wait_seconds)
    
    check_task_arrival(order_id, task_id)

def check_task_arrival(order_id: str, task_id: str):
    order = service_orders.get(order_id)
    if not order:
        return
    
    task = next((t for t in order.tasks if t.task_id == task_id), None)
    if not task:
        return
    
    task.checked_time = int(time.time() * 1000)
    card_id = task.assigned_card_id
    arrived = False
    
    if card_id in locations:
        loc = locations[card_id]
        if task.area_bounds:
            b = task.area_bounds
            if (b['minX'] <= loc.x <= b['maxX'] and 
                b['minY'] <= loc.y <= b['maxY']):
                arrived = True
        else:
            if loc.timestamp > (int(time.time() * 1000) - 40 * 60 * 1000):
                arrived = True
    
    if arrived:
        task.status = "arrived"
        task.arrived_time = int(time.time() * 1000)
        logger.info(f"订单{order_id} 任务{task_id} [{task.task_name}] 执行人{task.assigned_name} 已到位")
        
        try:
            session = Session()
            db_task = session.query(ServiceTaskDB).filter_by(order_id=order_id, task_id=task_id).first()
            if db_task:
                db_task.status = task.status
                db_task.arrived_time = task.arrived_time
                session.commit()
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
        finally:
            session.close()
        
        broadcast({
            "type": "task_updated",
            "data": {"order_id": order_id, "task": asdict(task)}
        })
    else:
        task.status = "timeout"
        logger.warning(f"订单{order_id} 任务{task_id} [{task.task_name}] 执行人{task.assigned_name} 超时未到位")
        
        try:
            session = Session()
            db_task = session.query(ServiceTaskDB).filter_by(order_id=order_id, task_id=task_id).first()
            if db_task:
                db_task.status = task.status
                db_task.checked_time = task.checked_time
                session.commit()
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
        finally:
            session.close()
        
        notify_task_timeout(order, task)
        broadcast({
            "type": "task_timeout",
            "data": {"order_id": order_id, "task": asdict(task)}
        })

def on_staff_enter_area(card_id: int, area_id: int, area_name: str):
    if card_id not in staff_stats:
        staff_name = locations[card_id].name if card_id in locations else f"未知-{card_id}"
        staff_stats[card_id] = StaffStayStat(card_id=card_id, staff_name=staff_name)
    
    stat = staff_stats[card_id]
    if stat.current_area_id != area_id:
        if stat.enter_time:
            duration = int((time.time() * 1000 - stat.enter_time) / (1000 * 60))
            stat.total_duration_today += duration
            logger.info(f"服务人员{stat.staff_name} 离开区域 {stat.current_area_name} 时长 {duration} 分钟")
        
        stat.current_area_id = area_id
        stat.current_area_name = area_name
        stat.enter_time = int(time.time() * 1000)
        logger.info(f"服务人员{stat.staff_name} 进入区域 {area_name}")
        
        for order_id, order in service_orders.items():
            for task in order.tasks:
                if (task.assigned_card_id == card_id and 
                    task.area_id == area_id and 
                    task.status == "pending"):
                    task.status = "arrived"
                    task.arrived_time = int(time.time() * 1000)
                    logger.info(f"订单{order_id} 任务{task.task_id} 提前到位")
                    broadcast({
                        "type": "task_updated",
                        "data": {"order_id": order_id, "task": asdict(task)}
                    })

def on_staff_leave_area(card_id: int, area_id: int):
    if card_id not in staff_stats:
        return
    
    stat = staff_stats[card_id]
    if stat.current_area_id == area_id and stat.enter_time:
        duration = int((time.time() * 1000 - stat.enter_time) / (1000 * 60))
        stat.total_duration_today += duration
        logger.info(f"服务人员{stat.staff_name} 离开区域 {stat.current_area_name} 本次时长 {duration} 分钟")
        
        for order_id, order in service_orders.items():
            for task in order.tasks:
                if (task.assigned_card_id == card_id and 
                    task.area_id == area_id and 
                    task.status == "arrived"):
                    task.leave_time = int(time.time() * 1000)
                    task.duration_minutes = duration
        
        stat.current_area_id = None
        stat.current_area_name = None
        stat.enter_time = None

def on_item_enter_area(item_id: int, area_id: int, area_name: str):
    if item_id not in item_stats:
        item_name = locations[item_id].name if item_id in locations else f"未知-{item_id}"
        item_type = locations[item_id].utype if item_id in locations else "item"
        item_stats[item_id] = ItemStayStat(item_id=item_id, item_name=item_name, item_type=item_type)
    
    stat = item_stats[item_id]
    if stat.current_area_id != area_id:
        if stat.enter_time:
            duration = int((time.time() * 1000 - stat.enter_time) / (1000 * 60))
            stat.total_duration_today += duration
            logger.info(f"物品{stat.item_name} 离开区域 {stat.current_area_name} 时长 {duration} 分钟")
        
        stat.current_area_id = area_id
        stat.current_area_name = area_name
        stat.enter_time = int(time.time() * 1000)
        logger.info(f"物品{stat.item_name} 进入区域 {area_name}")
    
    broadcast_item_stats()

def on_item_leave_area(item_id: int, area_id: int):
    if item_id not in item_stats:
        return
    
    stat = item_stats[item_id]
    if stat.current_area_id == area_id and stat.enter_time:
        duration = int((time.time() * 1000 - stat.enter_time) / (1000 * 60))
        stat.total_duration_today += duration
        logger.info(f"物品{stat.item_name} 离开区域 {stat.current_area_name} 本次时长 {duration} 分钟")
        
        try:
            session = Session()
            record = ItemStayRecordDB(
                item_id=item_id,
                item_name=stat.item_name,
                area_id=area_id,
                area_name=stat.current_area_name,
                enter_time=stat.enter_time,
                leave_time=int(time.time() * 1000),
                duration_minutes=duration
            )
            session.add(record)
            session.commit()
        except Exception as e:
            logger.error(f"保存物品记录失败: {e}")
        finally:
            session.close()
        
        stat.current_area_id = None
        stat.current_area_name = None
        stat.enter_time = None
    
    broadcast_item_stats()

def notify_task_timeout(order: ServiceOrder, task: ServiceTask):
    if not NOTIFICATION["enable"]:
        return
    
    if NOTIFICATION["feishu_webhook"]:
        content = {
            "msg_type": "post",
            "content": {
                "title": "⚠️ 服务任务超时未到位告警",
                "content": [
                    [{"tag": "text", "text": f"订单ID: {order.order_id}"}],
                    [{"tag": "text", "text": f"客户: {order.customer_name} 包厢: {order.room_number}"}],
                    [{"tag": "text", "text": f"任务: {task.task_name}"}],
                    [{"tag": "text", "text": f"执行人: {task.assigned_name}"}],
                    [{"tag": "text", "text": f"区域: {task.area_name}"}],
                    [{"tag": "text", "text": f"计划检查时间已到，超时未检测到到位，请注意跟进"}]
                ]
            }
        }
        try:
            requests.post(NOTIFICATION["feishu_webhook"], json=content)
            logger.info(f"已发送超时告警到飞书: 订单{order.order_id} 任务{task.task_id}")
        except Exception as e:
            logger.error(f"飞书通知失败: {e}")

def receive_business_webhook(payload):
    try:
        orders_data = payload.get("orders", []) if isinstance(payload, dict) else (payload if isinstance(payload, list) else [payload])
        
        for order_data in orders_data:
            order = order_data.get("order", order_data)
            order_id = str(order.get("order_sn", order.get("id", f"ORDER_{int(time.time())}")))
            shop_id = order.get("shop_id", 0)
            shop_name = order.get("shop_name", f"门店{shop_id}")
            room_id = order.get("room_id", 0)
            room_name = order.get("room_name", f"包厢{room_id}")
            created_at = order.get("created_at")
            customer_mobile = order.get("member_mobile", order.get("customer_name", "未知客人"))
            
            if isinstance(created_at, str):
                try:
                    create_time = int(datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)
                except:
                    create_time = int(time.time() * 1000)
            else:
                create_time = int(time.time() * 1000)
            
            task1_id = f"{order_id}_task1"
            scheduled_check_time_1 = create_time + 30 * 60 * 1000
            task1 = ServiceTask(
                task_id=task1_id,
                task_name="上热毛巾+开机套",
                assigned_card_id=0,
                assigned_name="待匹配技师",
                area_id=room_id,
                area_name=room_name,
                check_delay_minutes=30,
                scheduled_check_time=scheduled_check_time_1,
            )
            
            task2_id = f"{order_id}_task2"
            scheduled_check_time_2 = create_time + 60 * 60 * 1000
            task2 = ServiceTask(
                task_id=task2_id,
                task_name="定时清理台面",
                assigned_card_id=0,
                assigned_name="待匹配技师",
                area_id=room_id,
                area_name=room_name,
                check_delay_minutes=60,
                scheduled_check_time=scheduled_check_time_2,
            )
            
            service_order = ServiceOrder(
                order_id=order_id,
                customer_name=customer_mobile or "未知客人",
                room_number=room_name,
                service_area_id=room_id,
                service_area_name=room_name,
                create_time=create_time,
                tasks=[task1, task2]
            )
            
            add_service_order(service_order)
            logger.info(f"已接收fun360订单: {order_id} 门店: {shop_name} 包厢: {room_name}")
        
        return {"error_code": 0, "message": "success"}
    except Exception as e:
        logger.error(f"解析fun360 webhook失败: {e}")
        return {"error_code": 500, "message": str(e)}

def on_connect(client, userdata, flags, rc):
    logger.info(f"MQTT connected with code {rc}")
    for topic, qos in TOPICS:
        client.subscribe(topic, qos)
        logger.info(f"Subscribed: {topic}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        logger.debug(f"Received {msg.topic}: {len(payload)} items")
        
        if "card_now_info" in msg.topic:
            for card_id_str, data in payload.items():
                card_id = int(card_id_str)
                loc = Location(
                    card_id=card_id,
                    uuid=data.get("uuid", 0),
                    utype=data.get("utype", 0),
                    name=get_name(data),
                    x=data.get("card_x", 0),
                    y=data.get("card_y", 0),
                    z=data.get("card_z", 0),
                    floor_id=data.get("floor_id", 1),
                    floor_name=data.get("floor_name", ""),
                    building_id=data.get("building_id", 0),
                    building_name=data.get("building_name", ""),
                    scene_id=data.get("scene_id", 0),
                    scene_name=data.get("scene_name", ""),
                    timestamp=data.get("rec_server_time", 0),
                )
                locations[card_id] = loc
                broadcast({
                    "type": "location",
                    "data": asdict(loc)
                })
        
        elif "inarea" in msg.topic:
            area_id = payload.get("area_id")
            area_name = payload.get("area_name", "")
            card_id = payload.get("card_id")
            utype = payload.get("utype", 1)
            if card_id and area_id:
                if utype == 1:
                    on_staff_enter_area(card_id, area_id, area_name)
                elif utype == 5:
                    on_item_enter_area(card_id, area_id, area_name)
            
            broadcast({
                "type": "enter_area",
                "data": payload
            })
        
        elif "outarea" in msg.topic:
            area_id = payload.get("area_id")
            card_id = payload.get("card_id")
            utype = payload.get("utype", 1)
            if card_id and area_id:
                if utype == 1:
                    on_staff_leave_area(card_id, area_id)
                elif utype == 5:
                    on_item_leave_area(card_id, area_id)
            
            broadcast({
                "type": "leave_area",
                "data": payload
            })
        
        elif "alarm/start" in msg.topic:
            for alarm_data in payload:
                alarm = Alarm(
                    id=alarm_data.get("id"),
                    rule_type=alarm_data.get("rule_type"),
                    rule_name=alarm_data.get("rule_name"),
                    level=alarm_data.get("level"),
                    card_id=alarm_data.get("card_id"),
                    uuid=alarm_data.get("uuid"),
                    area_name=alarm_data.get("trigger_area"),
                    time=alarm_data.get("time"),
                    message=alarm_data.get("alarm_info"),
                )
                if alarm.card_id and alarm.card_id in locations:
                    locations[alarm.card_id].is_alarm = True
                    locations[alarm.card_id].alarm_info = alarm.message
                
                broadcast({
                    "type": "alarm_start",
                    "data": {
                        "alarm": alarm.__dict__,
                        "location": asdict(locations[alarm.card_id]) if alarm.card_id in locations else None
                    }
                })
        
        elif "alarm/stop" in msg.topic:
            for alarm_data in payload:
                alarm_id = alarm_data.get("id")
                rule_type = alarm_data.get("rule_type")
                card_id = None
                if "card_id" in alarm_data:
                    card_id = alarm_data.get("card_id")
                if card_id and card_id in locations:
                    locations[card_id].is_alarm = False
                    locations[card_id].alarm_info = None
                
                broadcast({
                    "type": "alarm_stop",
                    "data": {"id": alarm_id, "rule_type": rule_type, "card_id": card_id}
                })
                
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)

def get_name(data):
    utype = data.get("utype")
    card_id = data.get("card_id")
    if utype == 1:
        return f"员工-{card_id}"
    elif utype == 2:
        return f"车辆-{card_id}"
    elif utype == 3:
        return f"访客-{card_id}"
    elif utype == 5:
        return f"物品-{card_id}"
    return f"未知-{card_id}"

async def broadcast_async(message):
    if not connected_clients:
        return
    message_str = json.dumps(message)
    closed = set()
    for websocket in connected_clients:
        try:
            await websocket.send(message_str)
        except ConnectionClosed:
            closed.add(websocket)
    connected_clients.difference_update(closed)

def broadcast(message):
    loop = get_event_loop()
    try:
        asyncio.run_coroutine_threadsafe(broadcast_async(message), loop)
    except Exception as e:
        logger.error(f"广播失败: {e}")

async def handle_websocket(websocket):
    connected_clients.add(websocket)
    logger.info(f"New client connected, total: {len(connected_clients)}")
    await websocket.send(json.dumps({
        "type": "initial",
        "data": [asdict(loc) for loc in locations.values()]
    }))
    await websocket.send(json.dumps({
        "type": "initial_orders",
        "data": {order_id: asdict(order) for order_id, order in service_orders.items()}
    }))
    await websocket.send(json.dumps({
        "type": "item_stats_update",
        "data": {item_id: asdict(stat) for item_id, stat in item_stats.items()}
    }))
    try:
        async for message in websocket:
            pass
    finally:
        connected_clients.remove(websocket)
        logger.info(f"Client disconnected, total: {len(connected_clients)}")


def broadcast_item_stats():
    """广播物品统计更新到所有客户端"""
    broadcast({
        "type": "item_stats_update",
        "data": {item_id: asdict(stat) for item_id, stat in item_stats.items()}
    })

async def main():
    if MQTT_HOST and MQTT_HOST != "localhost":
        try:
            mqtt_client = mqtt.Client()
            mqtt_client.on_connect = on_connect
            mqtt_client.on_message = on_message
            if MQTT_USERNAME:
                mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            mqtt_client.connect(MQTT_HOST, MQTT_PORT)
            mqtt_client.loop_start()
            logger.info(f"MQTT client started on {MQTT_HOST}:{MQTT_PORT}")
        except Exception as e:
            logger.warning(f"MQTT连接失败: {e}，将以演示模式运行")
    else:
        logger.info("MQTT未配置，以演示模式运行")
    
    async with serve(handle_websocket, "0.0.0.0", WS_PORT):
        logger.info(f"WebSocket server started on port {WS_PORT}")
        await asyncio.Future()

app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)))

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        app_id = request.args.get('app_id', request.form.get('app_id', BUSINESS_API.get('app_id', '')))
        nonce = request.args.get('nonce', request.form.get('nonce', ''))
        timestamp = request.args.get('timestamp', request.form.get('timestamp', ''))
        sign = request.args.get('sign', request.form.get('sign', ''))
        
        payload = request.get_json(silent=True) or request.form.to_dict()
        
        logger.info(f"收到webhook请求: app_id={app_id}, nonce={nonce}, timestamp={timestamp}")
        
        if BUSINESS_API.get('app_secret'):
            if not verify_sign(app_id, BUSINESS_API['app_secret'], nonce, timestamp, sign):
                logger.warning(f"签名验证失败")
                return jsonify({"error_code": 401, "message": "签名验证失败"}), 401
        
        result = receive_business_webhook(payload)
        return jsonify(result)
    except Exception as e:
        logger.error(f"webhook error: {e}", exc_info=True)
        return jsonify({"error_code": 500, "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "running"})

@app.route('/test_order', methods=['POST'])
def test_order():
    try:
        data = request.get_json(silent=True) or {}
        order_id = data.get('order_id', f"TEST_{int(time.time())}")
        customer_name = data.get('customer_name', "测试用户")
        room_name = data.get('room_name', "测试包厢101")
        
        create_time = int(time.time() * 1000)
        
        task1 = ServiceTask(
            task_id=f"{order_id}_task1",
            task_name="上热毛巾+开机套",
            assigned_card_id=1001,
            assigned_name="测试技师1",
            area_id=1,
            area_name=room_name,
            check_delay_minutes=0.5,
            scheduled_check_time=create_time + 30 * 1000,
        )
        
        task2 = ServiceTask(
            task_id=f"{order_id}_task2",
            task_name="定时清理台面",
            assigned_card_id=1002,
            assigned_name="测试技师2",
            area_id=1,
            area_name=room_name,
            check_delay_minutes=1,
            scheduled_check_time=create_time + 60 * 1000,
        )
        
        service_order = ServiceOrder(
            order_id=order_id,
            customer_name=customer_name,
            room_number=room_name,
            service_area_id=1,
            service_area_name=room_name,
            create_time=create_time,
            tasks=[task1, task2]
        )
        
        add_service_order(service_order)
        
        return jsonify({"error_code": 0, "message": "测试订单创建成功", "order_id": order_id})
    except Exception as e:
        logger.error(f"创建测试订单失败: {e}", exc_info=True)
        return jsonify({"error_code": 500, "message": str(e)}), 500

@app.route('/test_location', methods=['POST'])
def test_location():
    try:
        data = request.get_json(silent=True) or {}
        card_id = data.get('card_id', 1001)
        name = data.get('name', f"员工-{card_id}")
        x = data.get('x', random.uniform(0, 150))
        y = data.get('y', random.uniform(0, 100))
        
        loc = Location(
            card_id=card_id,
            uuid=0,
            utype=1,
            name=name,
            x=x,
            y=y,
            z=0,
            floor_id=1,
            floor_name="1楼",
            building_id=1,
            building_name="主楼",
            scene_id=1,
            scene_name="大厅",
            timestamp=int(time.time()),
        )
        
        locations[card_id] = loc
        broadcast({
            "type": "location",
            "data": asdict(loc)
        })
        
        logger.info(f"添加测试定位: {name} at ({x:.2f}, {y:.2f})")
        
        return jsonify({"error_code": 0, "message": "测试定位添加成功", "location": asdict(loc)})
    except Exception as e:
        logger.error(f"添加测试定位失败: {e}", exc_info=True)
        return jsonify({"error_code": 500, "message": str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    return jsonify({
        "error_code": 0,
        "data": {order_id: asdict(order) for order_id, order in service_orders.items()}
    })

@app.route('/api/locations', methods=['GET'])
def get_locations():
    return jsonify({
        "error_code": 0,
        "data": [asdict(loc) for loc in locations.values()]
    })

@app.route('/test_item_location', methods=['POST'])
def test_item_location():
    try:
        data = request.get_json(silent=True) or {}
        card_id = data.get('card_id', 2001)
        name = data.get('name', f"物品-{card_id}")
        x = data.get('x', random.uniform(0, 150))
        y = data.get('y', random.uniform(0, 100))
        
        loc = Location(
            card_id=card_id,
            uuid=0,
            utype=5,  # 物品类型
            name=name,
            x=x,
            y=y,
            z=0,
            floor_id=1,
            floor_name="1楼",
            building_id=1,
            building_name="主楼",
            scene_id=1,
            scene_name="大厅",
            timestamp=int(time.time()),
        )
        
        locations[card_id] = loc
        broadcast({
            "type": "location",
            "data": asdict(loc)
        })
        
        logger.info(f"添加测试物品定位: {name} at ({x:.2f}, {y:.2f})")
        
        return jsonify({"error_code": 0, "message": "测试物品定位添加成功", "location": asdict(loc)})
    except Exception as e:
        logger.error(f"添加测试物品定位失败: {e}", exc_info=True)
        return jsonify({"error_code": 500, "message": str(e)}), 500

@app.route('/test_enter_area', methods=['POST'])
def test_enter_area():
    try:
        data = request.get_json(silent=True) or {}
        card_id = data.get('card_id', 1001)
        area_id = data.get('area_id', 1)
        area_name = data.get('area_name', "测试区域")
        utype = data.get('utype', 1)  # 1=人员 5=物品
        
        if utype == 1:
            on_staff_enter_area(card_id, area_id, area_name)
        else:
            on_item_enter_area(card_id, area_id, area_name)
        
        return jsonify({"error_code": 0, "message": "进入区域事件触发成功"})
    except Exception as e:
        logger.error(f"触发进入区域事件失败: {e}", exc_info=True)
        return jsonify({"error_code": 500, "message": str(e)}), 500

@app.route('/test_leave_area', methods=['POST'])
def test_leave_area():
    try:
        data = request.get_json(silent=True) or {}
        card_id = data.get('card_id', 1001)
        area_id = data.get('area_id', 1)
        utype = data.get('utype', 1)  # 1=人员 5=物品
        
        if utype == 1:
            on_staff_leave_area(card_id, area_id)
        else:
            on_item_leave_area(card_id, area_id)
        
        return jsonify({"error_code": 0, "message": "离开区域事件触发成功"})
    except Exception as e:
        logger.error(f"触发离开区域事件失败: {e}", exc_info=True)
        return jsonify({"error_code": 500, "message": str(e)}), 500

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/test')
def test_page():
    return send_from_directory(app.static_folder, 'test.html')

def start_flask():
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    global_loop = asyncio.new_event_loop()
    
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    logger.info(f"Flask webhook server started on port {FLASK_PORT}")
    logger.info(f"测试接口:")
    logger.info(f"  - POST /test_order  创建测试订单")
    logger.info(f"  - POST /test_location  添加测试定位")
    logger.info(f"  - GET /api/orders  获取订单列表")
    logger.info(f"  - GET /api/locations  获取定位列表")
    logger.info(f"  - POST /webhook  接收fun360订单推送")
    
    try:
        asyncio.set_event_loop(global_loop)
        global_loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"服务运行失败: {e}", exc_info=True)
