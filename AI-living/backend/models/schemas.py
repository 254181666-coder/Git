"""
数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# 枚举定义
class DriverMode(str, Enum):
    CAMERA = "camera"
    CACHE = "cache"
    ORIGINAL = "original"
    DUAL_AVATAR = "dual_avatar"
    SADTALKER = "sadtalker"

class PlayMode(str, Enum):
    RANDOM = "random"
    SEQUENTIAL = "sequential"

class AIDriver(str, Enum):
    OPENAI = "openai"
    SADTALKER = "sadtalker"

class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"

class PlanType(str, Enum):
    FREE = "free"
    MONTHLY = "monthly"
    PAY_AS_YOU_GO = "pay_as_you_go"

# 用户模型
class UserCreate(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    password: str

class UserResponse(BaseModel):
    id: str
    phone: Optional[str]
    email: Optional[str]
    status: UserStatus
    plan_type: PlanType
    remaining_minutes: float
    created_at: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[dict] = None

# 话术模型
class ScriptCreate(BaseModel):
    text: str
    face_id: Optional[str] = None
    voice_id: Optional[str] = None
    duration: Optional[float] = 0.0
    priority: Optional[int] = 0

class ScriptItem(BaseModel):
    id: str
    text: str
    face_id: Optional[str]
    voice_id: Optional[str]
    duration: float
    priority: int

# 直播模型
class StreamStartRequest(BaseModel):
    rtmp_url: str
    driver_mode: DriverMode = DriverMode.CAMERA
    ai_driver: AIDriver = AIDriver.OPENAI
    width: Optional[int] = 1080
    height: Optional[int] = 1920
    fps: Optional[int] = 30
    bitrate: Optional[int] = 4000
    enable_audio: Optional[bool] = True
    audio_bitrate: Optional[int] = 128
    audio_file: Optional[str] = None
    enable_anti_detect: Optional[bool] = True
    dry_run: Optional[bool] = False

class StatusResponse(BaseModel):
    is_streaming: bool
    is_scheduling: bool
    current_script: Optional[ScriptItem]
    ai_connected: bool
    driver_mode: str
    runtime_minutes: float

# AI模型
class AiGenerateRequest(BaseModel):
    text: str
    face_id: Optional[str] = None
    voice_id: Optional[str] = None
    driver: AIDriver = AIDriver.OPENAI

class ChatMessage(BaseModel):
    message: str
    product_info: Optional[str] = ""

class ChatResponse(BaseModel):
    response: str
    driver: str

class ProductInfoRequest(BaseModel):
    info: str = ""

# 数字人模型
class AvatarModeRequest(BaseModel):
    mode: DriverMode

class AvatarConfig(BaseModel):
    camera_id: Optional[int] = 0
    video_path: Optional[str] = None
    cache_path: Optional[str] = None
    secondary_avatar: Optional[str] = None

# 计费模型
class BillingRecord(BaseModel):
    id: str
    user_id: str
    start_time: str
    end_time: Optional[str]
    duration_minutes: float
    cost: float
    status: str

class UsageStats(BaseModel):
    total_minutes: float
    total_cost: float
    remaining_minutes: float
    current_month_usage: float
