"""
用户认证模块
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

from models.schemas import UserCreate, UserLogin, UserResponse, Token

router = APIRouter()

# 开发环境使用简单的hash方案，避免bcrypt密码长度限制
pwd_context = CryptContext(schemes=["plaintext"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")[:32]
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# 简单内存存储（生产环境应该使用数据库）
users_db = {}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def get_token_from_header(authorization: str = Header(None, alias="Authorization")) -> str:
    """从Header中提取Token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少Token")
    if authorization.startswith("Bearer "):
        return authorization.replace("Bearer ", "")
    return authorization

@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    """用户注册"""
    if user.email and any(u.get("email") == user.email for u in users_db.values()):
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    if user.phone and any(u.get("phone") == user.phone for u in users_db.values()):
        raise HTTPException(status_code=400, detail="手机号已被注册")
        
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user.password)
    
    users_db[user_id] = {
        "id": user_id,
        "phone": user.phone,
        "email": user.email,
        "password": hashed_password,
        "status": "active",
        "plan_type": "free",
        "remaining_minutes": float(os.getenv("FREE_DAILY_MINUTES", "30")),
        "created_at": datetime.utcnow().isoformat(),
        "total_usage_minutes": 0.0
    }
    
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": users_db[user_id]}

@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    """用户登录"""
    db_user = None
    for u in users_db.values():
        if (user.email and u.get("email") == user.email) or \
           (user.phone and u.get("phone") == user.phone):
            db_user = u
            break
            
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="账号或密码错误")
        
    access_token = create_access_token(
        data={"sub": db_user["id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": db_user}

@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(get_token_from_header)):
    """获取当前用户信息"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id not in users_db:
            raise HTTPException(status_code=401, detail="用户不存在")
        return users_db[user_id]
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的Token")