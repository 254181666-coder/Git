"""
工具函数
"""
import re
import requests
from config import STORE_PREFIXES, EXCLUDE_STORES, NAME_MAP, FEISHU_WEBHOOK_URL

def simplify_store_name(name):
    """统一门店名称格式"""
    if not name or not isinstance(name, str):
        return None

    name = name.strip()

    for prefix in STORE_PREFIXES:
        name = name.replace(prefix, "")

    name = name.replace("店", "").strip()

    if name in EXCLUDE_STORES:
        return None

    if name in NAME_MAP:
        name = NAME_MAP[name]

    return name if name else None


def send_feishu_notification(title: str, content: str) -> bool:
    """
    发送飞书机器人通知
    """
    if not FEISHU_WEBHOOK_URL:
        print("飞书Webhook未配置，跳过通知")
        return False
    
    message = {
        "msg_type": "text",
        "content": {
            "text": f"{title}\n\n{content}"
        }
    }
    
    try:
        resp = requests.post(FEISHU_WEBHOOK_URL, json=message, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 0:
            print("飞书通知发送成功")
            return True
        else:
            print(f"飞书通知发送失败: {result}")
            return False
    except Exception as e:
        print(f"飞书通知发送异常: {e}")
        return False
