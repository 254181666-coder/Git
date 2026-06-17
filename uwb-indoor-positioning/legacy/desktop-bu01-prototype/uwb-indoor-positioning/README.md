# UWB 室内定位系统 - 轨迹追踪

基于安信可 NodeMCU-BU01 (DW1000) 模块的室内人员/物品定位+轨迹追踪系统

## 系统架构

```
UWB标签 → UWB基站 → CP2102 USB-TTL → USB集线器 → 服务器 → MySQL数据库 → Web前端
```

## 硬件清单

| 物品 | 数量 | 说明 |
|------|------|------|
| NodeMCU-BU01开发板 | 5+ | 4个基站 + 1个标签起，可扩展 |
| CP2102 USB-TTL模块 | 5+ | 每块模块需要一个串口转换器 |
| 杜邦线（母对母） | 20+ | VCC/GND/TX/RX连接 |
| USB集线器（10口） | 1 | 集中连接多个串口模块 |
| USB充电头 | 5+ | 基站供电 |
| Type-C数据线 | 5+ | 供电和数据传输 |
| 外壳(可选) | 5+ | 3D打印或卖家配套 |

## 硬件连接

```
BU01开发板          CP2102 USB-TTL
    VCC  ───────→   3.3V
    GND  ───────→   GND
    TX   ───────→   RX    (交叉连接)
    RX   ───────→   TX    (交叉连接)
```

## 快速开始

### 1. 配置模块
通过串口连接每个模块，配置角色：

```bash
# 测试连接
AT

# 配置为基站
AT+ROLE=0

# 配置为标签
AT+ROLE=1

# 查询测距
AT+RANGE?
```

### 2. 修改配置
编辑 `backend/config.py`：

```python
# 基站坐标，单位：米
ANCHORS = [
    {"id": 0, "x": 0.0, "y": 0.0, "z": 3.0, "port": "/dev/tty.SLAB_USBtoUART0"},
    {"id": 1, "x": 0.0, "y": 8.0, "z": 3.0, "port": "/dev/tty.SLAB_USBtoUART1"},
    {"id": 2, "x": 10.0, "y": 8.0, "z": 3.0, "port": "/dev/tty.SLAB_USBtoUART2"},
    {"id": 3, "x": 10.0, "y": 0.0, "z": 3.0, "port": "/dev/tty.SLAB_USBtoUART3"},
]

# MySQL数据库配置
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "uwb_user",
    "password": "your_password",
    "database": "uwb_position",
    "charset": "utf8mb4"
}
```

### 3. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 4. 启动后端
```bash
python main.py
```

### 5. 访问前端
打开浏览器访问：`http://服务器IP:8000`

## 目录结构

```
├── README.md          # 本文件
├── SUMMARY.md         # 项目总结
├── backend/           # Python后端定位服务
│   ├── main.py        # 主服务入口（串口通信）
│   ├── config.py      # 配置文件（串口+MySQL）
│   ├── positioning.py # 三边定位算法+滤波
│   ├── database.py    # MySQL数据存储
│   └── requirements.txt
└── frontend/          # Web前端轨迹展示
    ├── index.html
    └── app.js
```

## AT指令集（核心常用）

| 指令 | 说明 | 示例 |
|------|------|------|
| AT | 测试连接 | `AT` → `OK` |
| AT+ROLE | 设置角色 | `AT+ROLE=0` 基站，`AT+ROLE=1` 标签 |
| AT+RANGE? | 查询距离 | `AT+RANGE?` → `+RANGE:0,1500` |
| AT+TDOA | TDOA模式 | `AT+TDOA=on` |
| AT+ADDR? | 查询地址 | `AT+ADDR?` |
| AT+RESET | 重启模块 | `AT+RESET` |

## 定位算法
使用经典三边定位算法，支持：
- 实时计算标签坐标
- 滑动平均滤波平滑轨迹
- 保存历史轨迹到MySQL数据库
- 轨迹回放
- 支持人员和物品两种标签类型

精度：一般 10~30cm，满足室内定位需求。

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/position | GET | 获取当前位置 |
| /api/history | GET | 获取历史轨迹 |
| /api/tags | GET/POST | 标签管理 |
| /api/rooms | GET/POST | 包厢管理 |
| /api/anchors | GET | 获取基站配置 |

## 注意事项

1. BU01模块使用3.3V供电，请勿接5V
2. 串口连接时TX-RX交叉连接
3. 需要提前在MySQL中创建数据库 `uwb_position`
4. Linux系统可能需要设置串口权限：`sudo chmod 666 /dev/tty.SLAB_USBtoUART*`
5. 每个位置需要被至少3个基站覆盖才能定位