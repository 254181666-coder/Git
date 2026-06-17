# UWB定位后端服务（KTV场景完整版）

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import serial
import serial.tools.list_ports
import time
import threading
import json
import re
import os
from datetime import datetime

from config import (
    ANCHORS, ROOMS, PUBLIC_AREAS,
    SERVER_HOST, SERVER_PORT,
    SERIAL_BAUDRATE, SERIAL_TIMEOUT,
    REFRESH_RATE, ENABLE_FILTER,
    UWB_OPTIMIZATION, FILTER_CONFIG,
    BUSINESS_CONFIG, INTERCOM_CONFIG
)
from positioning import (
    calculate_position, get_room_by_position,
    moving_average_filter, speed_filter, get_nearby_staff
)
from database import init_db, insert_position, get_history, get_latest


app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# 全局状态管理
class UWBSystemState:
    def __init__(self):
        self.serial_ports = {}          # 串口连接池
        self.current_positions = {}     # 当前位置 {tag_id: position_data}
        self.position_histories = {}    # 滤波历史 {tag_id: [positions]}
        self.last_positions = {}        # 上次位置 {tag_id: (x, y)}
        self.last_times = {}            # 上次时间戳 {tag_id: timestamp}
        self.anchor_distances = {}      # 基站测距数据 {anchor_id: distance}
        self.is_running = False         # 系统运行状态
        
state = UWBSystemState()


class UWBSerialManager:
    """UWB串口管理器"""
    
    def __init__(self):
        self.ports = {}
    
    def open_port(self, port_name):
        """打开串口连接"""
        if port_name in self.ports:
            return self.ports[port_name]
        
        try:
            ser = serial.Serial(
                port=port_name,
                baudrate=SERIAL_BAUDRATE,
                timeout=SERIAL_TIMEOUT,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            time.sleep(0.5)  # 等待串口稳定
            
            # 测试连接
            response = self.send_command(ser, 'AT')
            if response and 'OK' in response:
                print(f"[成功] 串口 {port_name} 已连接")
                self.ports[port_name] = ser
                return ser
            else:
                print(f"[警告] 串口 {port_name} 无响应")
                ser.close()
                return None
                
        except Exception as e:
            print(f"[错误] 打开串口 {port_name} 失败: {e}")
            return None
    
    def send_command(self, ser, command, wait_time=0.5):
        """发送AT指令并获取响应"""
        try:
            # 清空输入缓冲区
            ser.reset_input_buffer()
            
            # 发送指令
            ser.write((command + '\r\n').encode('utf-8'))
            time.sleep(wait_time)
            
            # 读取响应
            response = ''
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore')
                response += line
            
            return response.strip()
            
        except Exception as e:
            print(f"[错误] 发送指令失败: {e}")
            return None
    
    def configure_anchor(self, port_name, anchor_id):
        """配置基站"""
        ser = self.open_port(port_name)
        if not ser:
            return False
        
        commands = [
            ('AT+ROLE=0', '设置基站模式'),
            ('AT+TXPOWER=' + UWB_OPTIMIZATION['tx_power'], '设置发射功率'),
        ]
        
        for cmd, desc in commands:
            response = self.send_command(ser, cmd)
            if response and 'OK' in response:
                print(f"[基站{anchor_id}] {desc} 成功")
            else:
                print(f"[警告] 基站{anchor_id} {desc} 失败: {response}")
        
        return True
    
    def configure_tag(self, port_name, tag_id):
        """配置标签"""
        ser = self.open_port(port_name)
        if not ser:
            return False
        
        commands = [
            ('AT+ROLE=1', '设置标签模式'),
            ('AT+TXPOWER=' + UWB_OPTIMIZATION['tx_power'], '设置发射功率'),
        ]
        
        for cmd, desc in commands:
            response = self.send_command(ser, cmd)
            if response and 'OK' in response:
                print(f"[标签{tag_id}] {desc} 成功")
            else:
                print(f"[警告] 标签{tag_id} {desc} 失败: {response}")
        
        return True
    
    def get_distance(self, port_name, anchor_id):
        """获取测距数据"""
        ser = self.ports.get(port_name)
        if not ser:
            ser = self.open_port(port_name)
        
        if not ser:
            return None
        
        try:
            response = self.send_command(ser, 'AT+RANGE?', 1.0)
            if response:
                # 解析响应格式: +RANGE:target_id,distance_mm
                match = re.search(r'\+RANGE:(\d+),(\d+)', response)
                if match:
                    target_id = int(match.group(1))
                    distance_mm = int(match.group(2))
                    distance_m = distance_mm / 1000.0
                    
                    # 验证距离有效性
                    is_valid, _ = validate_distance(distance_m, anchor_id)
                    if is_valid:
                        return {
                            "anchor_id": anchor_id,
                            "target_id": target_id,
                            "distance": distance_m,
                            "timestamp": time.time()
                        }
                    
            return None
            
        except Exception as e:
            print(f"[错误] 获取距离失败 (基站{anchor_id}): {e}")
            return None
    
    def close_all(self):
        """关闭所有串口"""
        for port_name, ser in self.ports.items():
            try:
                ser.close()
                print(f"[信息] 关闭串口 {port_name}")
            except:
                pass
        self.ports.clear()


serial_manager = UWBSerialManager()


def validate_distance(distance, anchor_id=None):
    """验证测距有效性"""
    max_dist = UWB_OPTIMIZATION["max_valid_distance"]
    min_dist = UWB_OPTIMIZATION["min_valid_distance"]
    
    if min_dist <= distance <= max_dist:
        return True, distance
    
    if anchor_id is not None:
        print(f"[警告] 基站{anchor_id} 距离异常: {distance:.2f}m")
    
    return False, None


def positioning_loop():
    """后台定位主循环"""
    state.is_running = True
    print("[系统] 定位服务启动...")
    
    init_db()
    
    # 初始化所有基站连接
    print("[初始化] 连接所有基站...")
    for anchor in ANCHORS:
        success = serial_manager.configure_anchor(anchor['port'], anchor['id'])
        if success:
            print(f"  ✓ 基站 {anchor['id']} 已就绪 (端口: {anchor['port']})")
        else:
            print(f"  ✗ 基站 {anchor['id']} 连接失败")
    
    print("\n[运行] 开始定位循环...")
    
    while state.is_running:
        loop_start_time = time.time()
        
        # 收集所有基站的测距数据
        all_distances = []
        
        for anchor in ANCHORS:
            dist_data = serial_manager.get_distance(anchor['port'], anchor['id'])
            if dist_data:
                all_distances.append(dist_data)
                
                # 记录到全局状态
                state.anchor_distances[anchor['id']] = dist_data
                
                print(f"  基站{anchor['id']}: 距离={dist_data['distance']:.2f}m "
                      f"(目标:{dist_data['target_id']})")
        
        # 如果有足够的测距数据，进行定位
        if len(all_distances) >= UWB_OPTIMIZATION["min_anchors_for_positioning"]:
            # 按标签ID分组
            tag_groups = {}
            for dist in all_distances:
                tag_id = dist['target_id']
                if tag_id not in tag_groups:
                    tag_groups[tag_id] = []
                tag_groups[tag_id].append({
                    "anchor_id": dist['anchor_id'],
                    "distance": dist['distance']
                })
            
            # 对每个标签进行定位
            for tag_id, distances in tag_groups.items():
                position_result = calculate_position(tag_id, distances)
                
                if position_result.get("success"):
                    pos = position_result["position"]
                    x, y = pos["x"], pos["y"]
                    current_time = position_result["timestamp"]
                    
                    # 应用速度过滤
                    last_pos = state.last_positions.get(tag_id)
                    last_time = state.last_times.get(tag_id)
                    
                    if ENABLE_FILTER:
                        is_valid, filtered_pos = speed_filter(
                            (x, y), last_pos, last_time, current_time
                        )
                        
                        if is_valid:
                            x, y = filtered_pos
                        
                        # 应用滑动平均滤波
                        if tag_id not in state.position_histories:
                            state.position_histories[tag_id] = []
                        
                        filtered_pos, history = moving_average_filter(
                            (x, y), 
                            state.position_histories[tag_id]
                        )
                        state.position_histories[tag_id] = history
                        x, y = filtered_pos
                    
                    # 更新状态
                    final_position = {
                        "tag_id": tag_id,
                        "position": {"x": round(x, 3), "y": round(y, 3)},
                        "confidence": position_result.get("confidence", 0),
                        "room": position_result.get("room", "未知"),
                        "room_type": position_result.get("room_type", "未知"),
                        "anchor_count": len(distances),
                        "timestamp": current_time
                    }
                    
                    state.current_positions[tag_id] = final_position
                    state.last_positions[tag_id] = (x, y)
                    state.last_times[tag_id] = current_time
                    
                    # 存储到数据库
                    insert_position(
                        tag_id=tag_id,
                        x=x,
                        y=y,
                        room_no=final_position["room"],
                        confidence=final_position["confidence"]
                    )
                    
                    print(f"\n[定位] 标签{tag_id}: ({x:.2f}, {y:.2f}) "
                          f"| 包房: {final_position['room']} "
                          f"| 置信度: {final_position['confidence']:.2%}\n")
        
        # 控制循环频率
        elapsed = time.time() - loop_start_time
        sleep_time = max(0, (1.0 / REFRESH_RATE) - elapsed)
        time.sleep(sleep_time)


@app.route('/api/position/current')
def get_current_position():
    """获取当前所有标签的最新位置"""
    positions = list(state.current_positions.values())
    return jsonify({
        "success": True,
        "count": len(positions),
        "positions": positions,
        "timestamp": time.time()
    })


@app.route('/api/position/<int:tag_id>')
def get_tag_position(tag_id):
    """获取指定标签的最新位置"""
    position = state.current_positions.get(tag_id)
    if position:
        return jsonify({"success": True, "position": position})
    else:
        return jsonify({
            "success": False,
            "message": f"标签 {tag_id} 无位置数据"
        }), 404


@app.route('/api/history')
def get_history_api():
    """获取历史轨迹"""
    tag_id = request.args.get('tag_id', default=0, type=int)
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    limit = request.args.get('limit', default=100, type=int)
    
    history = get_history(tag_id, start_time, end_time, limit)
    return jsonify({
        "success": True,
        "count": len(history),
        "history": history
    })


@app.route('/api/anchors/status')
def get_anchors_status():
    """获取基站状态"""
    anchors_status = []
    for anchor in ANCHORS:
        anchor_info = {
            "id": anchor['id'],
            "x": anchor['x'],
            "y": anchor['y'],
            "z": anchor['z'],
            "port": anchor['port'],
            "connected": anchor['port'] in serial_manager.ports,
            "last_distance": state.anchor_distances.get(anchor['id'])
        }
        anchors_status.append(anchor_info)
    
    return jsonify({
        "success": True,
        "anchors": anchors_status
    })


@app.route('/api/system/status')
def get_system_status():
    """获取系统状态"""
    return jsonify({
        "success": True,
        "status": {
            "is_running": state.is_running,
            "online_tags": len(state.current_positions),
            "connected_anchors": len(serial_manager.ports),
            "total_anchors": len(ANCHORS),
            "uptime": time.time(),
            "config": {
                "refresh_rate": REFRESH_RATE,
                "filter_enabled": ENABLE_FILTER,
                "max_distance": UWB_OPTIMIZATION["max_valid_distance"],
                "tx_power": UWB_OPTIMIZATION["tx_power"]
            }
        }
    })


@app.route('/api/staff/nearby')
def get_nearby_staff_api():
    """查询附近的服务人员"""
    room_no = request.args.get('room_no')
    radius = request.args.get('radius', default=None, type=float)
    
    if not room_no:
        return jsonify({"success": False, "message": "缺少包房号参数"}), 400
    
    # 获取所有人员标签的位置
    staff_positions = []
    for tag_id, pos_data in state.current_positions.items():
        if pos_data.get("room_type") == "人员":
            staff_positions.append({
                "id": tag_id,
                "x": pos_data["position"]["x"],
                "y": pos_data["position"]["y"]
            })
    
    nearby = get_nearby_staff(room_no, staff_positions, radius)
    
    return jsonify({
        "success": True,
        "room": room_no,
        "nearby_count": len(nearby),
        "staff": nearby
    })


@app.route('/api/config/rooms')
def get_rooms_config():
    """获取包房区域配置"""
    return jsonify({
        "success": True,
        "rooms": ROOMS,
        "public_areas": PUBLIC_AREAS
    })


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "message": "API不存在"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "message": "服务器内部错误"}), 500


def cleanup():
    """清理资源"""
    print("\n[系统] 正在关闭...")
    state.is_running = False
    serial_manager.close_all()
    print("[系统] 资源已释放")


if __name__ == '__main__':
    import atexit
    atexit.register(cleanup)
    
    # 启动定位线程
    positioning_thread = threading.Thread(target=positioning_loop, daemon=True)
    positioning_thread.start()
    
    print("=" * 60)
    print("  UWB室内定位系统 - KTV版")
    print("=" * 60)
    print(f"  服务地址: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"  基站数量: {len(ANCHORS)}")
    print(f"  刷新频率: {REFRESH_RATE} Hz")
    print(f"  滤波器: {'启用' if ENABLE_FILTER else '禁用'}")
    print("=" * 60)
    
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, use_reloader=False)
