"""
计费模块 - SaaS化核心
"""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter
from typing import Dict, List

from models.schemas import BillingRecord, UsageStats

router = APIRouter()

# 简单内存存储（生产环境应该使用数据库）
billing_records: Dict[str, List[Dict]] = {}

HOURLY_RATE = float(os.getenv("HOURLY_RATE", "1.0"))
MONTHLY_RATE = float(os.getenv("MONTHLY_RATE", "99.0"))

@router.post("/start")
async def start_billing(user_id: str):
    """开始计费"""
    if user_id not in billing_records:
        billing_records[user_id] = []
        
    record = {
        "id": str(len(billing_records[user_id]) + 1),
        "user_id": user_id,
        "start_time": datetime.utcnow().isoformat(),
        "end_time": None,
        "duration_minutes": 0.0,
        "cost": 0.0,
        "status": "running"
    }
    billing_records[user_id].append(record)
    return {"status": "ok", "message": "计费已开始", "record_id": record["id"]}

@router.post("/stop")
async def stop_billing(user_id: str, record_id: str):
    """停止计费"""
    if user_id not in billing_records:
        return {"status": "error", "message": "用户不存在"}
        
    for record in billing_records[user_id]:
        if record["id"] == record_id and record["status"] == "running":
            record["end_time"] = datetime.utcnow().isoformat()
            start = datetime.fromisoformat(record["start_time"])
            end = datetime.fromisoformat(record["end_time"])
            duration = (end - start).total_seconds() / 60.0
            record["duration_minutes"] = duration
            record["cost"] = duration * HOURLY_RATE / 60.0
            record["status"] = "completed"
            return {
                "status": "ok",
                "duration_minutes": duration,
                "cost": record["cost"]
            }
            
    return {"status": "error", "message": "记录不存在或已完成"}

@router.get("/usage/{user_id}")
async def get_usage_stats(user_id: str):
    """获取用户使用统计"""
    if user_id not in billing_records:
        return UsageStats(
            total_minutes=0.0,
            total_cost=0.0,
            remaining_minutes=30.0,
            current_month_usage=0.0
        )
        
    total_minutes = sum(r["duration_minutes"] for r in billing_records[user_id])
    total_cost = sum(r["cost"] for r in billing_records[user_id])
    
    # 本月使用统计
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_month_usage = sum(
        r["duration_minutes"] for r in billing_records[user_id]
        if datetime.fromisoformat(r["start_time"]) >= month_start
    )
    
    return UsageStats(
        total_minutes=total_minutes,
        total_cost=total_cost,
        remaining_minutes=max(0, 30.0 - current_month_usage),
        current_month_usage=current_month_usage
    )

@router.get("/history/{user_id}")
async def get_billing_history(user_id: str):
    """获取计费历史"""
    if user_id not in billing_records:
        return {"status": "ok", "records": []}
    return {"status": "ok", "records": billing_records[user_id]}