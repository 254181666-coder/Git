"""
UWB监控系统配置模板
请复制此文件为 config.py 并填写真实配置
"""

# ========== MQTT 配置（四相恒迹云） ==========
MQTT_HOST = "your-mqtt-host"        # MQTT服务器地址
MQTT_PORT = 1883                    # MQTT端口
MQTT_USERNAME = "your-username"     # MQTT用户名
MQTT_PASSWORD = "your-password"     # MQTT密码
TENANT_ID = 1                       # 你的租户ID

# ========== WebSocket 配置 ==========
WS_PORT = 8765                      # WebSocket服务端口

# ========== 服务监控配置 ==========
CHECK_DELAY_MINUTES = 30            # 开单后默认检查延迟（分钟）

# ========== 通知配置 ==========
NOTIFICATION = {
    "enable": True,
    "feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/your-key",  # 飞书机器人webhook
    "sms_enable": False,             # 是否启用短信
    "admin_notify_phone": "",        # 管理员告警手机号
}

# ========== 业务系统API配置（fun360） ==========
BUSINESS_API = {
    "base_url": "https://open-api.fun360.cn",
    "app_id": "YYP",                 # 你的app_id
    "app_secret": "your-secret",     # 你的app_secret
    "enable_polling": False,         # 是否轮询拉取
}

# ========== 数据库配置 ==========
# SQLite（默认，无需额外配置）
DATABASE_URL = "sqlite:///./uwb_monitoring.db"
# MySQL（可选）
# DATABASE_URL = "mysql+pymysql://username:password@host:port/uwb_monitoring"

# ========== Flask HTTP 服务 ==========
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 8000
