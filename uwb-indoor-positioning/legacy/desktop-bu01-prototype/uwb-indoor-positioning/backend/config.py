# UWB定位系统 - 配置文件（KTV场景优化版）

# ========== 基站配置 ==========
# 请根据你的实际房间尺寸修改坐标，单位：米
# 格式：[{"id": 基站编号, "x": X坐标, "y": Y坐标, "z": Z坐标(高度), "port": 串口号}, ...]
ANCHORS = [
    {"id": 0, "x": 0.0, "y": 0.0, "z": 3.0, "port": "/dev/tty.SLAB_USBtoUART0"},
    {"id": 1, "x": 0.0, "y": 8.0, "z": 3.0, "port": "/dev/tty.SLAB_USBtoUART1"},
    {"id": 2, "x": 10.0, "y": 8.0, "z": 3.0, "port": "/dev/tty.SLAB_USBtoUART2"},
    {"id": 3, "x": 10.0, "y": 0.0, "z": 3.0, "port": "/dev/tty.SLAB_USBtoUART3"},
]

# Windows系统串口号示例（根据实际情况修改）
# ANCHORS = [
#     {"id": 0, "x": 0.0, "y": 0.0, "z": 3.0, "port": "COM3"},
#     {"id": 1, "x": 0.0, "y": 8.0, "z": 3.0, "port": "COM4"},
#     {"id": 2, "x": 10.0, "y": 8.0, "z": 3.0, "port": "COM5"},
#     {"id": 3, "x": 10.0, "y": 0.0, "z": 3.0, "port": "COM6"},
# ]

# ========== KTV包房区域定义 ==========
# 定义每个包房的边界范围，用于判断标签所在位置
# 单位：米
ROOMS = {
    # 普通包房 (4m x 4m)
    "K01": {"x_min": 0, "x_max": 4, "y_min": 0, "y_max": 4, "type": "普通"},
    "K02": {"x_min": 4, "x_max": 8, "y_min": 0, "y_max": 4, "type": "普通"},
    "K03": {"x_min": 8, "x_max": 12, "y_min": 0, "y_max": 4, "type": "普通"},
    "K04": {"x_min": 0, "x_max": 4, "y_min": 4, "y_max": 8, "type": "普通"},
    "K05": {"x_min": 4, "x_max": 8, "y_min": 4, "y_max": 8, "type": "普通"},
    "K06": {"x_min": 8, "x_max": 12, "y_min": 4, "y_max": 8, "type": "普通"},
    
    # 豪华包房 (6m x 5m)
    "V01": {"x_min": 0, "x_max": 6, "y_min": 8, "y_max": 13, "type": "豪华"},
    "V02": {"x_min": 6, "x_max": 12, "y_min": 8, "y_max": 13, "type": "豪华"},
    
    # VIP包房 (8m x 6m)
    "VIP01": {"x_min": 0, "x_max": 8, "y_min": 13, "y_max": 19, "type": "VIP"},
    "VIP02": {"x_min": 8, "x_max": 16, "y_min": 13, "y_max": 19, "type": "VIP"},
}

# 公共区域定义
PUBLIC_AREAS = {
    "大厅": {"x_min": 16, "x_max": 20, "y_min": 0, "y_max": 19},
    "走廊": {"x_min": 0, "x_max": 16, "y_min": 19, "y_max": 21},
    "前台": {"x_min": 18, "x_max": 22, "y_min": 19, "y_max": 23},
}

# ========== 网络配置 ==========
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# ========== 串口配置 ==========
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 2

# ========== KTV场景优化参数 ==========
UWB_OPTIMIZATION = {
    # 有效测距距离阈值（米）- 忽略过远的异常值
    "max_valid_distance": 8.0,
    "min_valid_distance": 0.1,
    
    # 发射功率控制（减少穿墙干扰）
    # 可选值: "low", "medium", "high"
    "tx_power": "medium",
    
    # 最少有效基站数（用于定位）
    "min_anchors_for_positioning": 3,
    
    # 异常值剔除参数
    "outlier_threshold": 50.0,  # cm - 超过此值的跳变视为异常
    
    # 区域边界缓冲区（米）
    # 标签在边界附近时给予一定容错空间
    "boundary_buffer": 0.3,
}

# ========== 算法配置 ==========
REFRESH_RATE = 5

ENABLE_FILTER = True

# 滤波器参数
FILTER_CONFIG = {
    # 滑动平均窗口大小
    "window_size": 7,
    
    # 最大允许跳变速度（米/秒）
    # 超过此速度的位置变化会被过滤
    "max_speed": 3.0,
    
    # 卡尔曼滤波参数（可选）
    "kalman_enabled": False,
    "process_noise": 0.01,
    "measurement_noise": 0.1,
}

# ========== MySQL数据库配置 ==========
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "uwb_user",
    "password": "your_password",
    "database": "uwb_position",
    "charset": "utf8mb4"
}

# ========== 业务系统对接配置 ==========
BUSINESS_CONFIG = {
    "enabled": True,
    # API轮询间隔（秒）
    "sync_interval": 30,
    
    # 服务提醒延迟（秒）
    "service_remind_delay": 1800,  # 开台后30分钟
    
    # 清洁提醒延迟（秒）
    "cleaning_delay": 60,  # 关台后1分钟
    
    # 人员搜索半径（米）
    "staff_search_radius": 10,
    "cleaner_search_radius": 15,
    
    # 业务系统API地址（待填写）
    "business_api_url": "",
    "api_key": "",
}

# ========== 对讲系统配置 ==========
INTERCOM_CONFIG = {
    "enabled": True,
    # 对讲系统网关地址（待填写）
    "gateway_url": "",
    "gateway_api_key": "",
    
    # 通知模板
    "service_template": "{staff_name}，请前往{room_no}包房服务",
    "cleaning_template": "{cleaner_name}，请前往{room_no}包房清洁",
}
