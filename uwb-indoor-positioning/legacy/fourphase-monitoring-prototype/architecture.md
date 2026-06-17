# UWB定位监控自建系统 - 项目档案

## 项目概述

- **目标**: 基于四相科技恒迹云UWB系统接口，自建管理动作监控
- **数据源**: MQTT实时推送 + HTTP REST API查询
- **输出**: 实时地图展示 + 告警监控

## 接口文档

- MQTT v7.0.0: `MQTT文档-v7.0.0.docx` - 实时定位、告警推送
- HTTP API v7.1.0: `API文档_V7.1.0.docx` - 基础数据查询、统计

## 项目架构

```
┌─────────────┐
│  四相UWB系统 │
└──────┬──────┘
       │
       ├─ MQTT → 实时定位/alarms
       │
       └─ HTTP API → 人员/车辆/访客基础信息
             │
             ▼
       ┌──────────────────┐
       │  backend.py      │  - MQTT订阅
       │  (Python)       │  - WebSocket广播
       │                 │  - 点位状态缓存
       └────────┬───────┘
                │
                ▼
       ┌──────────────────┐
       │  WebSocket       │
       └────────┬───────┘
                │
                ▼
       ┌──────────────────┐
       │  index.html      │  - OpenLayers 地图
       │  (Browser)      │  - 实时点位更新
       │                 │  - 楼层切换
       │                 │  - 告警列表
       └──────────────────┘
```

## 文件清单

| 文件                | 说明                            |
| ----------------- | ----------------------------- |
| `backend.py`      | Python后端服务，MQTT订阅 + WebSocket |
| `index.html`      | 前端地图展示，OpenLayers             |
| `README.md`       | 部署说明                          |
| `architecture.md` | 本文档，整体架构说明                    |

## 核心配置项

### 后端 (`backend.py`)

```python
MQTT_HOST = "your-mqtt-host"
MQTT_PORT = 1883
MQTT_USERNAME = "username"
MQTT_PASSWORD = "password"
TENANT_ID = 1
WS_PORT = 8765
```

### 前端 (`index.html`)

```javascript
const UWB_BOUNDS = {
  minX: 0, maxX: 150,  // 实际物理范围，单位米
  minY: 0, maxY: 100,
};

const FLOORS = [
  {
    id: 1,
    name: '1楼',
    imageUrl: './floor-1.png',  // 楼层平面图
    imageWidth: 1500,
    imageHeight: 1000,
  }
];
```

## 点位类型

| utype | 类型  | 颜色      |
| ----- | --- | ------- |
| 0     | 陌生卡 | #9E9E9E |
| 1     | 人员  | #2196F3 |
| 2     | 车辆  | #FF9800 |
| 3     | 访客  | #4CAF50 |
| 4     | 车厢卡 | #9C27B0 |
| 5     | 物资  | #795548 |
| 6     | 承包商 | #607D8B |

## MQTT订阅Topic

```python
TOPICS = [
    (f"/{TENANT_ID}/pos_business/card_now_info/#", 0),  # 实时定位
    (f"/{TENANT_ID}/pos_business/inarea", 0),           # 进入区域
    (f"/{TENANT_ID}/pos_business/outarea", 0),          # 离开区域
    (f"/{TENANT_ID}/alarm/start/#", 0),                 # 所有告警开始
    (f"/{TENANT_ID}/alarm/stop/#", 0),                  # 所有告警结束
]
```

## 消息类型 (WebSocket -> 前端)

| type          | 说明            |
| ------------- | ------------- |
| `initial`     | 连接建立，发送全量当前点位 |
| `location`    | 点位位置更新        |
| `alarm_start` | 告警开始          |
| `alarm_stop`  | 告警结束          |

## 已实现功能

- ✅ MQTT连接和自动订阅
- ✅ 实时点位更新广播
- ✅ 告警状态关联到点位
- ✅ OpenLayers矢量地图展示
- ✅ 楼层切换
- ✅ 左侧边栏统计
- ✅ 活跃告警列表
- ✅ 告警点位红色高亮
- ✅ 点击点位弹出详情
- ✅ WebSocket自动重连

## 待开发/扩展

1. **HTTP API对接** - 完善 `get_name()` 函数，从API获取真实人员/车辆名称
2. **数据持久化** - 添加数据库存储历史轨迹和告警
3. **轨迹回放** - 按时间查询历史位置，前端动画回放
4. **离线清理** - 定时清除N分钟没更新的离线标签
5. **区域高亮** - 告警区域多边形高亮显示
6. **告警通知** - 接入企业微信/钉钉/短信告警推送

## 部署命令

```bash
# 安装依赖
pip install paho-mqtt websockets

# 开发运行
python backend.py &

# 后台运行（supervisor配置见README.md）
```

## 创建时间

2026-04-20

## 作者

AI 全能流程研发设计师 - 根据需求生成框架
