# 三边定位算法实现（KTV场景优化版）

import numpy as np
from config import ANCHORS, UWB_OPTIMIZATION, ROOMS, PUBLIC_AREAS, FILTER_CONFIG


def validate_distance(distance, anchor_id=None):
    """
    验证测距数据的有效性
    
    参数:
        distance: 测距值（米）
        anchor_id: 基站ID（可选，用于日志记录）
    
    返回:
        (is_valid, distance): 是否有效, 处理后的距离值
    """
    max_dist = UWB_OPTIMIZATION["max_valid_distance"]
    min_dist = UWB_OPTIMIZATION["min_valid_distance"]
    
    if min_dist <= distance <= max_dist:
        return True, distance
    
    # 记录异常值日志（可选）
    if anchor_id is not None:
        print(f"[警告] 基站{anchor_id}测距异常: {distance:.2f}m (有效范围: {min_dist}-{max_dist}m)")
    
    return False, None


def filter_outliers(distances, anchors):
    """
    过滤异常测距值
    
    使用基于统计的方法剔除明显错误的测量值
    
    参数:
        distances: 测距列表 [d1, d2, ...]
        anchors: 对应的基站列表
    
    返回:
        (valid_distances, valid_anchors): 有效的距离和基站
    """
    valid_distances = []
    valid_anchors = []
    
    for i, (dist, anchor) in enumerate(zip(distances, anchors)):
        is_valid, processed_dist = validate_distance(dist, anchor.get('id', i))
        
        if is_valid:
            # 检查跳变是否过大
            if len(valid_distances) > 0:
                avg_dist = np.mean(valid_distances)
                jump = abs(processed_dist - avg_dist)
                threshold = UWB_OPTIMIZATION["outlier_threshold"] / 100  # cm转m
                
                if jump < threshold:
                    valid_distances.append(processed_dist)
                    valid_anchors.append(anchor)
                else:
                    print(f"[警告] 检测到跳变: 基站{i} 距离={processed_dist:.2f}m, 平均={avg_dist:.2f}m")
            else:
                valid_distances.append(processed_dist)
                valid_anchors.append(anchor)
    
    return valid_distances, valid_anchors


def weighted_trilateration(anchors, distances):
    """
    加权三边定位算法
    
    根据测距质量对定位结果进行加权处理，
    距离越近、信号越强的基站权重越高
    
    参数:
        anchors: 基站列表 [{"x": x1, "y": y1}, ...]
        distances: 对应基站到标签的距离列表 [d1, d2, ...]
    
    返回:
        (x, y, confidence): 标签坐标和置信度(0-1)
    """
    # 需要至少3个基站才能定位
    min_anchors = UWB_OPTIMIZATION["min_anchors_for_positioning"]
    
    if len(anchors) < min_anchors or len(distances) < min_anchors:
        return None, None, 0.0
    
    # 先过滤异常值
    valid_distances, valid_anchors = filter_outliers(distances, anchors)
    
    if len(valid_anchors) < min_anchors:
        return None, None, 0.0
    
    # 转换为numpy数组
    x = np.array([a['x'] for a in valid_anchors])
    y = np.array([a['y'] for a in valid_anchors])
    d = np.array(valid_distances)
    
    # 计算权重：距离越近权重越高
    weights = 1.0 / (d + 0.1)  # 避免除零
    weights = weights / np.sum(weights)  # 归一化
    
    try:
        # 构建加权最小二乘方程组
        A = []
        b = []
        
        for i in range(1, len(valid_anchors)):
            row = [
                2 * (x[i] - x[0]) * weights[i],
                2 * (y[i] - y[0]) * weights[i]
            ]
            A.append(row)
            
            val = (d[0]**2 - d[i]**2 + x[i]**2 - x[0]**2 + y[i]**2 - y[0]**2) * weights[i]
            b.append(val)
        
        A = np.array(A)
        b = np.array(b)
        
        # 求解方程组
        solution = np.linalg.lstsq(A, b, rcond=None)[0]
        pos_x, pos_y = solution[0], solution[1]
        
        # 计算置信度（基于残差）
        residuals = A @ solution - b
        confidence = max(0, 1 - np.mean(np.abs(residuals)) / 10)
        
        return pos_x, pos_y, confidence
        
    except Exception as e:
        print(f"[错误] 定位计算失败: {e}")
        return None, None, 0.0


def get_room_by_position(x, y):
    """
    根据坐标判断标签所在的包房或区域
    
    参数:
        x: X坐标（米）
        y: Y坐标（米）
    
    返回:
        (area_name, area_type): 区域名称和类型
    """
    buffer = UWB_OPTIMIZATION["boundary_buffer"]
    
    # 检查包房区域
    for room_no, bounds in ROOMS.items():
        x_in = bounds["x_min"] - buffer <= x <= bounds["x_max"] + buffer
        y_in = bounds["y_min"] - buffer <= y <= bounds["y_max"] + buffer
        
        if x_in and y_in:
            return room_no, bounds["type"]
    
    # 检查公共区域
    for area_name, bounds in PUBLIC_AREAS.items():
        x_in = bounds["x_min"] - buffer <= x <= bounds["x_max"] + buffer
        y_in = bounds["y_min"] - buffer <= y <= bounds["y_max"] + buffer
        
        if x_in and y_in:
            return area_name, "公共"
    
    # 未识别区域
    return "未知", "未知"


def speed_filter(new_pos, last_pos, last_time, current_time):
    """
    速度过滤：过滤掉不合理的快速移动
    
    参数:
        new_pos: 新位置 (x, y)
        last_pos: 上次位置 (x, y)
        last_time: 上次时间戳
        current_time: 当前时间戳
    
    返回:
        (is_valid, filtered_pos): 是否有效, 过滤后的位置
    """
    max_speed = FILTER_CONFIG["max_speed"]
    
    if last_pos is None or last_time is None:
        return True, new_pos
    
    # 计算时间差（秒）
    dt = current_time - last_time
    if dt <= 0:
        return True, new_pos
    
    # 计算距离（米）
    dx = new_pos[0] - last_pos[0]
    dy = new_pos[1] - last_pos[1]
    distance = np.sqrt(dx**2 + dy**2)
    
    # 计算速度（米/秒）
    speed = distance / dt
    
    if speed > max_speed:
        print(f"[警告] 检测到超速移动: {speed:.2f}m/s (最大允许: {max_speed}m/s)")
        return False, last_pos  # 返回上次位置
    
    return True, new_pos


def moving_average_filter(new_pos, history, window_size=None):
    """
    滑动平均滤波，平滑轨迹
    
    参数:
        new_pos: 新测量位置 (x, y)
        history: 历史位置列表
        window_size: 窗口大小（默认使用配置文件中的值）
    
    返回:
        (filtered_pos, history): 滤波后的位置和更新后的历史记录
    """
    if window_size is None:
        window_size = FILTER_CONFIG["window_size"]
    
    history.append(new_pos)
    if len(history) > window_size:
        history.pop(0)
    
    x_avg = sum(p[0] for p in history) / len(history)
    y_avg = sum(p[1] for p in history) / len(history)
    
    return (x_avg, y_avg), history


def calculate_position(tag_id, raw_distances):
    """
    完整的定位流程
    
    整合所有优化算法，提供完整的定位服务
    
    参数:
        tag_id: 标签ID
        raw_distances: 原始测距数据 [{anchor_id: distance}, ...]
    
    返回:
        position_data: 包含位置、置信度、所在区域的完整信息字典
    """
    import time
    
    # 提取有效的测距数据
    anchors = []
    distances = []
    
    for dist_data in raw_distances:
        anchor_id = dist_data.get("anchor_id")
        distance = dist_data.get("distance")
        
        # 找到对应的基站信息
        anchor = next((a for a in ANCHORS if a['id'] == anchor_id), None)
        
        if anchor and distance is not None:
            anchors.append(anchor)
            distances.append(distance)
    
    # 执行加权定位
    x, y, confidence = weighted_trilateration(anchors, distances)
    
    if x is None or y is None:
        return {
            "tag_id": tag_id,
            "success": False,
            "error": "无法定位",
            "timestamp": time.time()
        }
    
    # 判断所在区域
    room_no, room_type = get_room_by_position(x, y)
    
    return {
        "tag_id": tag_id,
        "success": True,
        "position": {"x": round(x, 3), "y": round(y, 3)},
        "confidence": round(confidence, 3),
        "room": room_no,
        "room_type": room_type,
        "anchor_count": len(anchors),
        "timestamp": time.time()
    }


def get_nearby_staff(target_room, staff_positions, radius=None):
    """
    查找指定包房附近的服务人员
    
    参数:
        target_room: 目标包房号
        staff_positions: 服务员位置列表 [{id, x, y}, ...]
        radius: 搜索半径（米），默认使用配置值
    
    返回:
        sorted_staff: 按距离排序的服务员列表
    """
    if radius is None:
        radius = BUSINESS_CONFIG["staff_search_radius"] if 'BUSINESS_CONFIG' in dir() else 10
    
    # 获取目标包房中心坐标
    room_info = ROOMS.get(target_room)
    if not room_info:
        return []
    
    center_x = (room_info["x_min"] + room_info["x_max"]) / 2
    center_y = (room_info["y_min"] + room_info["y_max"]) / 2
    
    nearby_staff = []
    
    for staff in staff_positions:
        sx = staff.get("x", 0)
        sy = staff.get("y", 0)
        
        # 计算距离
        distance = np.sqrt((sx - center_x)**2 + (sy - center_y)**2)
        
        if distance <= radius:
            nearby_staff.append({
                **staff,
                "distance_to_target": round(distance, 2)
            })
    
    # 按距离排序
    nearby_staff.sort(key=lambda s: s["distance_to_target"])
    
    return nearby_staff
