#!/usr/bin/env python3
from fastapi import FastAPI, Depends, HTTPException, Query, Body, UploadFile, File, Request
from pydantic import BaseModel, validator
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date, timedelta
from calendar import monthrange
from models import (engine, SessionLocal, Base, Store, Employee, AttendanceRecord, LeaveRequest, SalaryRecord, AttendanceSettings, init_default_settings, PositionAttendanceRule, AttendanceResult, SalaryRule, User, OperationLog, SalaryImportBatch, SalaryDraft, SalaryAuditResult, SalaryStandard)
from config import get_settings
from security import hash_password, verify_password
import locale
import json
import secrets
import io
import pandas as pd
try:
    locale.setlocale(locale.LC_ALL, 'Chinese (Simplified)_China.936')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'chs')
    except:
        pass

settings = get_settings()
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

rate_limit_storage = {}
RATE_LIMIT = settings.RATE_LIMIT
RATE_WINDOW = settings.RATE_WINDOW

def parse_time_to_hour(time_str):
    clean = time_str.replace('次日', '').strip()
    try:
        return int(clean.split(':')[0])
    except:
        return 0

def parse_rule_time_minutes(time_str):
    clean = str(time_str or "").replace("次日", "").replace("：", ":").strip()
    try:
        hour, minute = clean.split(":")[:2]
        return int(hour) * 60 + int(minute)
    except:
        return 0

def circular_minute_distance(a, b):
    diff = abs(a - b)
    return min(diff, 1440 - diff)

def _table_columns(conn, table_name):
    dialect = engine.dialect.name
    if dialect == "sqlite":
        return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()}
    return {row[0] for row in conn.exec_driver_sql(f"SHOW COLUMNS FROM {table_name}").fetchall()}

def _add_column_if_missing(conn, table_name, column_name, column_type):
    if column_name not in _table_columns(conn, table_name):
        conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

def ensure_runtime_columns():
    migrations = {
        "salary_rules": {
            "personal_leave_2h_deduct": "FLOAT DEFAULT 0",
            "late_count_deduct_tiers": "VARCHAR(1000) DEFAULT ''",
            "missing_deduct_tiers": "VARCHAR(1000) DEFAULT ''",
            "late_count_penalty_tiers": "VARCHAR(1000) DEFAULT ''",
            "absent_extra_penalty": "FLOAT DEFAULT 0",
            "missing_check_deduct": "FLOAT DEFAULT 0",
            "allow_late_count": "INTEGER DEFAULT 0",
            "allow_abnormal_count": "INTEGER DEFAULT 0",
            "allow_late_minutes": "FLOAT DEFAULT 0",
            "allow_early_leave_minutes": "FLOAT DEFAULT 0",
            "allow_sick_leave_days": "FLOAT DEFAULT 0",
            "allow_personal_leave_days": "FLOAT DEFAULT 0",
            "allow_personal_leave_2h_count": "INTEGER DEFAULT 0",
            "allow_missing_count": "INTEGER DEFAULT 0",
            "allow_absent_days": "FLOAT DEFAULT 0",
        },
        "salary_standards": {
            "allow_late_minutes": "FLOAT DEFAULT 0",
            "allow_early_leave_minutes": "FLOAT DEFAULT 0",
            "allow_sick_leave_days": "FLOAT DEFAULT 0",
            "allow_personal_leave_days": "FLOAT DEFAULT 0",
            "allow_personal_leave_2h_count": "INTEGER DEFAULT 0",
            "allow_missing_count": "INTEGER DEFAULT 0",
            "allow_absent_days": "FLOAT DEFAULT 0",
        },
        "salary_records": {
            "store_id": "INTEGER",
            "full_attendance_bonus": "FLOAT DEFAULT 0",
            "allowance": "FLOAT DEFAULT 0",
            "seniority_bonus": "FLOAT DEFAULT 0",
            "late_minutes": "INTEGER DEFAULT 0",
            "early_leave_minutes": "INTEGER DEFAULT 0",
            "absent_days": "FLOAT DEFAULT 0",
            "sick_leave_days": "FLOAT DEFAULT 0",
            "personal_leave_days": "FLOAT DEFAULT 0",
            "personal_leave_2h_count": "INTEGER DEFAULT 0",
            "missing_count": "INTEGER DEFAULT 0",
            "late_deduct": "FLOAT DEFAULT 0",
            "late_count_deduct": "FLOAT DEFAULT 0",
            "early_leave_deduct": "FLOAT DEFAULT 0",
            "absent_deduct": "FLOAT DEFAULT 0",
            "sick_leave_deduct": "FLOAT DEFAULT 0",
            "personal_leave_deduct": "FLOAT DEFAULT 0",
            "personal_leave_2h_deduct": "FLOAT DEFAULT 0",
            "missing_deduct": "FLOAT DEFAULT 0",
            "total_deduct": "FLOAT DEFAULT 0",
            "is_full_attendance": "BOOLEAN DEFAULT 0",
            "is_final": "BOOLEAN DEFAULT 0",
            "confirmed_by": "VARCHAR(100)",
            "confirmed_at": "DATETIME",
        },
    }
    with engine.begin() as conn:
        for table_name, columns in migrations.items():
            for column_name, column_type in columns.items():
                _add_column_if_missing(conn, table_name, column_name, column_type)
        if engine.dialect.name != "sqlite":
            conn.exec_driver_sql("ALTER TABLE salary_records MODIFY COLUMN work_days FLOAT DEFAULT 0")
            conn.exec_driver_sql("ALTER TABLE salary_records MODIFY COLUMN actual_work_days FLOAT DEFAULT 0")
            conn.exec_driver_sql("ALTER TABLE salary_records MODIFY COLUMN leave_days FLOAT DEFAULT 0")

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    client_ip = get_client_ip(request)
    path = request.url.path

    if path.startswith("/api/") and not path.startswith("/api/login"):
        now = datetime.now()
        key = f"{client_ip}:{path}"

        if key not in rate_limit_storage:
            rate_limit_storage[key] = []

        rate_limit_storage[key] = [t for t in rate_limit_storage[key] if (now - t).seconds < RATE_WINDOW]
        rate_limit_storage[key].append(now)

        if len(rate_limit_storage[key]) > RATE_LIMIT:
            return JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后再试"})

    response = await call_next(request)
    return response

def get_client_ip(request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

cors_origins = settings.CORS_ORIGINS
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    error_msg = str(exc)
    error_trace = traceback.format_exc()
    print(f"全局异常: {error_msg}")
    print(f"堆栈: {error_trace}")
    return JSONResponse(status_code=500, content={"detail": f"服务器内部错误: {error_msg}"})

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

class AttendanceResultUpdate(BaseModel):
    result_morning: str = None
    result_afternoon: str = None
    late_minutes: int = None
    early_leave_minutes: int = None
    remarks: str = None
    status: str = None
    confirmed_by: str = None
    updated_by: str = None
    is_resigned: bool = None

class ManualAttendanceCreate(BaseModel):
    store_id: int = None
    name: str
    date: str
    check_in: str = None
    check_out: str = None
    status: str = "正常"

class StoreCreate(BaseModel):
    code: str
    name: str
    city: str = ""
    address: str = ""
    manager: str = ""

    @validator('code')
    def validate_code(cls, v):
        if not v or not v.strip():
            raise ValueError('店面代码不能为空')
        if len(v) > 50:
            raise ValueError('店面代码不能超过50个字符')
        return v.strip().upper()

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('店面名称不能为空')
        if len(v) > 100:
            raise ValueError('店面名称不能超过100个字符')
        return v.strip()

class PositionRuleCreate(BaseModel):
    store_id: int
    position: str
    start_time: str
    end_time: str
    is_overnight: bool = False
    is_rotating_shift: bool = False
    base_salary: float = 0
    full_attendance_bonus: float = 0
    allowance: float = 0
    public_leave_days: float = 0

    @validator('start_time', 'end_time')
    def validate_time(cls, v):
        import re
        if not re.match(r'^\d{1,2}:\d{2}$', v):
            raise ValueError('时间格式必须为 HH:MM')
        return v

    @validator('position')
    def validate_position(cls, v):
        if not v or not v.strip():
            raise ValueError('岗位名称不能为空')
        return v.strip()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_operation(db, operator: str, action: str, target_type: str, target_id: int = None, target_name: str = None, details: str = None, ip_address: str = None):
    log = OperationLog(
        operator=operator or "系统",
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        details=details or "",
        ip_address=ip_address or ""
    )
    db.add(log)

def can_confirm_attendance(record, pos_rule=None):
    if record.result_morning == "正常" or record.result_afternoon == "正常":
        return True
    if record.result_morning in ["公休", "病假", "事假", "事假两小时"] or record.result_afternoon in ["公休", "病假", "事假", "事假两小时"]:
        return True
    if pos_rule and pos_rule.is_rotating_shift:
        return True
    if record.check_in_time or record.check_out_time:
        return True
    return False

def build_attendance_summary(records):
    summary = {
        "total": len(records),
        "normal": 0,
        "late": 0,
        "early": 0,
        "absent": 0,
        "missing": 0,
        "leave": 0,
        "pending": 0,
        "confirmed": 0,
    }
    for record in records:
        morning = record.result_morning or ""
        afternoon = record.result_afternoon or ""
        if record.status == "confirmed":
            summary["confirmed"] += 1
        else:
            summary["pending"] += 1
        if morning == "正常" and afternoon == "正常":
            summary["normal"] += 1
        if is_late_result(morning, record.late_minutes):
            summary["late"] += 1
        if is_early_result(afternoon, record.early_leave_minutes):
            summary["early"] += 1
        if record.is_full_day_absent or morning == "旷工" or afternoon == "旷工":
            summary["absent"] += 1
        if is_missing_result(morning) or is_missing_result(afternoon) or morning == "待确认" or afternoon == "待确认" or (not record.check_in_time and not record.check_out_time):
            summary["missing"] += 1
        if morning in ["公休", "病假", "事假", "事假两小时"] or afternoon in ["公休", "病假", "事假", "事假两小时"]:
            summary["leave"] += 1
    return summary

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=data.username,
        password_hash=hash_password(data.password)
    )
    db.add(user)
    db.commit()
    log_operation(db, "系统", "创建", "用户", user.id, user.username, "用户注册")
    return {"message": "注册成功", "user_id": user.id}

@app.post("/api/auth/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username, User.is_active == True).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = secrets.token_urlsafe(32)
    return {
        "message": "登录成功",
        "user_id": user.id,
        "username": user.username,
        "token": token
    }

@app.get("/api/auth/me")
def get_current_user(db: Session = Depends(get_db)):
    return {"message": "需要认证"}

@app.on_event("startup")
def startup_event():
    # 只初始化默认设置，表创建已在models.py中完成
    # Base.metadata.create_all 只创建不存在的表，不会覆盖已有数据
    init_default_settings()
    try:
        ensure_runtime_columns()
    except Exception as e:
        print(f"数据库字段检查失败: {e}")

@app.get("/")
async def root():
    return FileResponse("index.html", media_type="text/html")

@app.get("/api/stores", response_model=List[dict])
def get_stores(db: Session = Depends(get_db)):
    stores = db.query(Store).filter(Store.is_active == True).all()
    return [{"id": s.id, "code": s.code, "name": s.name, "city": s.city, "address": s.address, "manager": s.manager, "is_active": s.is_active} for s in stores]


@app.get("/api/stores/{store_id}", response_model=dict)
def get_store(store_id: int, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
    if not store:
        raise HTTPException(status_code=404, detail="店面不存在")
    return {
        "id": store.id,
        "code": store.code,
        "name": store.name,
        "city": store.city,
        "address": store.address,
        "manager": store.manager,
        "is_active": store.is_active,
    }


login_attempts = {}

@app.post("/api/login")
def login(data: dict, request: Request, db: Session = Depends(get_db)):
    username = data.get("username", "")
    password = data.get("password", "")

    client_ip = get_client_ip(request)
    if client_ip in login_attempts:
        if login_attempts[client_ip]["locked_until"]:
            if datetime.now() < login_attempts[client_ip]["locked_until"]:
                remaining = (login_attempts[client_ip]["locked_until"] - datetime.now()).seconds
                return {"success": False, "message": f"登录过于频繁，请{remaining}秒后重试"}
            else:
                login_attempts[client_ip] = {"count": 0, "locked_until": None}

    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        if client_ip in login_attempts:
            login_attempts[client_ip] = {"count": 0, "locked_until": None}
        return {"success": True, "token": secrets.token_urlsafe(32)}
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if user and verify_password(password, user.password_hash):
        if client_ip in login_attempts:
            login_attempts[client_ip] = {"count": 0, "locked_until": None}
        return {"success": True, "token": secrets.token_urlsafe(32)}

    if client_ip not in login_attempts:
        login_attempts[client_ip] = {"count": 0, "locked_until": None}
    login_attempts[client_ip]["count"] += 1
    if login_attempts[client_ip]["count"] >= 5:
        login_attempts[client_ip]["locked_until"] = datetime.now() + timedelta(minutes=15)
        return {"success": False, "message": "登录失败次数过多，请15分钟后再试"}
    return {"success": False, "message": "用户名或密码错误"}

@app.post("/api/stores")
def create_store(data: StoreCreate, db: Session = Depends(get_db)):
    existing = db.query(Store).filter(Store.code == data.code).first()
    if existing:
        existing.name = data.name
        existing.city = data.city
        existing.address = data.address
        existing.manager = data.manager
        existing.is_active = True
        db.commit()
        log_operation(db, "系统", "修改", "店面", existing.id, existing.name, f"更新店面信息")
        return {"message": "店面已更新", "id": existing.id}
    store = Store(code=data.code, name=data.name, city=data.city, address=data.address, manager=data.manager)
    db.add(store)
    db.commit()
    log_operation(db, "系统", "创建", "店面", store.id, store.name, f"新建店面，代码:{store.code}")
    return {"message": "店面创建成功", "id": store.id}

@app.put("/api/stores/{store_id}")
def update_store(store_id: int, data: StoreCreate, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店面不存在")
    store.name = data.name
    store.city = data.city
    store.address = data.address
    store.manager = data.manager
    db.commit()
    return {"message": "店面已修改", "id": store_id}

@app.delete("/api/stores/{store_id}")
def delete_store(store_id: int, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店面不存在")
    store_name = store.name
    store.is_active = False
    db.commit()
    log_operation(db, "系统", "删除", "店面", store_id, store_name, "软删除店面")
    return {"message": "店面已删除", "id": store_id}

@app.get("/api/logs")
def get_operation_logs(
    target_type: str = None,
    action: str = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(OperationLog)
    if target_type:
        query = query.filter(OperationLog.target_type == target_type)
    if action:
        query = query.filter(OperationLog.action == action)
    total = query.count()
    logs = query.order_by(OperationLog.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "logs": [{
            "id": log.id,
            "operator": log.operator,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "target_name": log.target_name,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None
        } for log in logs]
    }

@app.get("/api/stores/staffing-summary")
def get_stores_staffing_summary(db: Session = Depends(get_db)):
    stores = db.query(Store).filter(Store.is_active == True).order_by(Store.code).all()
    result = []
    for store in stores:
        employees = db.query(Employee).filter(Employee.store_id == store.id, Employee.is_active == True).all()
        positions = {}
        for emp in employees:
            pos = emp.position or "未分配"
            positions[pos] = positions.get(pos, 0) + 1
        result.append({
            "store_id": store.id,
            "store_name": store.name,
            "positions": positions,
            "total_count": len(employees)
        })
    return result

class SalaryRuleCreate(BaseModel):
    store_id: int
    late_deduct_tiers: str = ""  # JSON: [{"min":0,"max":10,"deduct":20},{"min":10,"max":60,"deduct":120}]
    late_count_deduct_tiers: str = ""
    missing_deduct_tiers: str = ""
    late_count_penalty_tiers: str = ""
    early_leave_deduct_per_minute: float = 0
    absent_multiplier: float = 2  # 旷工扣款倍数
    absent_extra_penalty: float = 0
    sick_leave_deduct_per_day: float = 1  # 病假扣款按日工资金额倍数
    personal_leave_deduct_per_day: float = 2  # 事假扣款按日工资金额倍数
    personal_leave_2h_deduct: float = 0  # 事假两小时扣款金额/次
    missing_check_deduct: float = 0  # 未打卡扣款金额/次
    allow_late_count: int = 0
    allow_abnormal_count: int = 0
    allow_late_minutes: float = 0
    allow_early_leave_minutes: float = 0
    allow_sick_leave_days: float = 0
    allow_personal_leave_days: float = 0
    allow_personal_leave_2h_count: int = 0
    allow_missing_count: int = 0
    allow_absent_days: float = 0

class SalaryStandardCreate(BaseModel):
    store_id: int
    position: str
    base_salary: float = 0
    full_attendance_bonus: float = 0
    allowance: float = 0
    public_leave_days: float = 0
    standard_work_days: float = 0
    min_net_salary: float = 0
    max_net_salary: float = 0
    # 满勤判断标准
    allow_late_minutes: float = 0
    allow_early_leave_minutes: float = 0
    allow_sick_leave_days: float = 0
    allow_personal_leave_days: float = 0
    allow_personal_leave_2h_count: int = 0
    allow_missing_count: int = 0
    allow_absent_days: float = 0
    description: str = ""

    @validator('position')
    def validate_standard_position(cls, v):
        if not v or not v.strip():
            raise ValueError("岗位不能为空")
        return v.strip()


class BatchConfirmRequest(BaseModel):
    store_id: int
    start_date: str
    end_date: str
    confirmed_by: str

class SalaryAuditReviewRequest(BaseModel):
    status: str
    reviewer: str = ""
    review_note: str = ""

    @validator('status')
    def validate_status(cls, v):
        allowed = ["pending", "confirmed", "returned", "ignored"]
        if v not in allowed:
            raise ValueError("状态必须为 pending/confirmed/returned/ignored")
        return v

def parse_money(value):
    if value is None:
        return 0.0
    try:
        text = str(value).strip()
        if not text or text.lower() == "nan":
            return 0.0
        text = text.replace(",", "").replace("￥", "").replace("¥", "")
        return float(text)
    except:
        return 0.0

def clean_optional_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None

def first_existing(row, columns):
    for col in columns:
        if col in row and row[col] is not None:
            value = row[col]
            try:
                import pandas as pd
                if pd.isna(value):
                    continue
            except:
                pass
            return value
    return None

def normalize_header_text(value):
    if value is None:
        return ""
    text = str(value).strip()
    text = text.replace("\n", "").replace("\r", "")
    text = text.replace(" ", "").replace("\u3000", "")
    return text

def load_salary_draft_dataframe(contents):
    import pandas as pd
    import io

    raw = pd.read_excel(io.BytesIO(contents), sheet_name=0, header=None)
    header_row = None
    for i in range(min(12, len(raw))):
        labels = [normalize_header_text(v) for v in raw.iloc[i].tolist()]
        if any(v in ["姓名", "姓名"] or "姓名" in v for v in labels) and any(v in ["实发工资", "实际发放", "实发"] for v in labels):
            header_row = i
            break
    if header_row is None:
        return pd.read_excel(io.BytesIO(contents))

    sub_header_row = header_row + 1 if header_row + 1 < len(raw) else None
    header_values = raw.iloc[header_row].tolist()
    sub_values = raw.iloc[sub_header_row].tolist() if sub_header_row is not None else [None] * len(header_values)
    columns = []
    seen = {}
    last_group = ""
    for idx, value in enumerate(header_values):
        header = normalize_header_text(value)
        sub = normalize_header_text(sub_values[idx]) if idx < len(sub_values) else ""
        if header:
            last_group = header
        final = header or sub
        if sub and header in ["奖励补助", "考勤扣款", "店面费用扣款", "五险一金扣款"]:
            final = f"{header}_{sub}"
        elif sub and not header and last_group in ["奖励补助", "考勤扣款", "店面费用扣款", "五险一金扣款"]:
            final = f"{last_group}_{sub}"
        elif sub and not header:
            final = sub
        if not final:
            final = f"未命名{idx + 1}"
        seen[final] = seen.get(final, 0) + 1
        if seen[final] > 1:
            final = f"{final}_{seen[final]}"
        columns.append(final)

    start_row = header_row + 2
    df = raw.iloc[start_row:].copy()
    df.columns = columns
    df = df.dropna(how='all')
    return df

def month_range(year, month):
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])

def summarize_employee_attendance(db, employee_id, year, month, confirmed_only=False):
    start, end = month_range(year, month)
    query = db.query(AttendanceResult).filter(
        AttendanceResult.employee_id == employee_id,
        AttendanceResult.date >= start,
        AttendanceResult.date <= end
    )
    if confirmed_only:
        query = query.filter(AttendanceResult.status == "confirmed")
    records = query.all()
    summary = {
        "records": len(records),
        "normal_days": 0,
        "late_days": 0,
        "late_events": [],
        "late_minutes": 0,
        "early_leave_days": 0,
        "early_leave_minutes": 0,
        "missing_count": 0,
        "sick_leave_days": 0,
        "personal_leave_days": 0,
        "personal_leave_2h_count": 0,
        "absent_days": 0,
        "public_leave_days": 0,
        "attendance_credit_days": 0,
        "is_resigned": False,
    }
    for r in records:
        morning = r.result_morning or ""
        afternoon = r.result_afternoon or ""
        summary["late_minutes"] += r.late_minutes or 0
        summary["early_leave_minutes"] += r.early_leave_minutes or 0
        if is_late_result(morning, r.late_minutes):
            summary["late_days"] += 1
            summary["late_events"].append(r.late_minutes or result_minutes(morning, "迟到", 0) or 0)
        if is_early_result(afternoon, r.early_leave_minutes):
            summary["early_leave_days"] += 1
        for half in [morning, afternoon]:
            if half == "正常" or half.startswith("迟到") or half.startswith("早退"):
                summary["normal_days"] += 0.5
            elif "缺卡" in half or half == "待确认":
                summary["missing_count"] += 1
                summary["normal_days"] += 0.5
            elif half == "病假":
                summary["sick_leave_days"] += 0.5
            elif half == "事假":
                summary["personal_leave_days"] += 0.5
            elif half == "事假两小时":
                summary["personal_leave_2h_count"] += 1
            elif half == "旷工":
                summary["absent_days"] += 0.5
            elif half == "公休":
                summary["public_leave_days"] += 0.5
            elif half == "离职":
                summary["is_resigned"] = True
    summary["attendance_credit_days"] = summary["normal_days"] + summary["public_leave_days"]
    return summary

def get_salary_standard_record(db, emp):
    return db.query(SalaryStandard).filter(
        SalaryStandard.store_id == emp.store_id,
        SalaryStandard.position == emp.position,
        SalaryStandard.is_active == True
    ).first()

def full_attendance_limit(salary_standard, salary_rule, field_name):
    standard_value = getattr(salary_standard, field_name, 0) if salary_standard else 0
    if standard_value and standard_value > 0:
        return standard_value
    return getattr(salary_rule, field_name, 0) if salary_rule else 0

def get_effective_hire_date(emp):
    if not emp or not emp.hire_date:
        return None
    if emp.created_at and emp.hire_date == emp.created_at.date():
        return None
    return emp.hire_date

def evaluate_full_attendance(attendance_summary, salary_standard, calendar_days, salary_rule=None, emp=None, year=None, month=None):
    should_rest_days = get_standard_rest_days(emp, salary_standard) if emp else ((salary_standard.public_leave_days if salary_standard and salary_standard.public_leave_days else 0) or 0)
    attendance_with_position_rest = attendance_summary.get("normal_days", 0) + should_rest_days
    employed_in_month = True
    if emp and year and month:
        _, month_end = month_range(year, month)
        hire_date = get_effective_hire_date(emp)
        employed_in_month = not (hire_date and hire_date > month_end)
    abnormal_limit = full_attendance_limit(salary_standard, salary_rule, "allow_abnormal_count") or 0
    abnormal_count = attendance_summary.get("late_days", 0) + attendance_summary.get("early_leave_days", 0) + attendance_summary.get("missing_count", 0)
    checks = {
        "late_count": attendance_summary.get("late_days", 0) <= (full_attendance_limit(salary_standard, salary_rule, "allow_late_count") or 0),
        "abnormal_count": True if abnormal_limit <= 0 else abnormal_count <= abnormal_limit,
        "late_minutes": attendance_summary["late_minutes"] <= (full_attendance_limit(salary_standard, salary_rule, "allow_late_minutes") or 0),
        "early_leave_minutes": attendance_summary["early_leave_minutes"] <= (full_attendance_limit(salary_standard, salary_rule, "allow_early_leave_minutes") or 0),
        "personal_leave_days": attendance_summary["personal_leave_days"] <= (full_attendance_limit(salary_standard, salary_rule, "allow_personal_leave_days") or 0),
        "personal_leave_2h_count": attendance_summary["personal_leave_2h_count"] <= (full_attendance_limit(salary_standard, salary_rule, "allow_personal_leave_2h_count") or 0),
        "missing_count": attendance_summary["missing_count"] <= (full_attendance_limit(salary_standard, salary_rule, "allow_missing_count") or 0),
        "absent_days": attendance_summary["absent_days"] <= (full_attendance_limit(salary_standard, salary_rule, "allow_absent_days") or 0),
        "attendance_days": attendance_with_position_rest >= calendar_days,
        "employed_in_month": employed_in_month,
        "not_resigned": not attendance_summary["is_resigned"],
    }
    return all(checks.values()), checks

def get_standard_rest_days(emp, salary_standard):
    if salary_standard and (salary_standard.public_leave_days or 0) > 0:
        return salary_standard.public_leave_days or 0
    return emp.public_leave_days or 0

def employment_days_in_month(emp, year, month):
    start, end = month_range(year, month)
    hire_date = get_effective_hire_date(emp)
    if hire_date and hire_date > end:
        return 0
    effective_start = max(start, hire_date) if hire_date else start
    return max(0, (end - effective_start).days + 1)

def calculate_payable_days(emp, attendance_summary, salary_standard, year, month):
    calendar_days = monthrange(year, month)[1]
    employment_days = employment_days_in_month(emp, year, month)
    if employment_days <= 0:
        return 0, 0, 0, get_standard_rest_days(emp, salary_standard), True
    should_rest_days = get_standard_rest_days(emp, salary_standard)
    attendance_with_position_rest = attendance_summary.get("normal_days", 0) + should_rest_days
    payable_days = min(employment_days, attendance_with_position_rest)
    overtime_days = max(0, attendance_with_position_rest - employment_days)
    is_partial_month = employment_days < calendar_days
    return round(payable_days, 2), round(overtime_days, 2), employment_days, should_rest_days, is_partial_month

def repair_split_day_checkins(employee_date_records):
    repaired = 0
    for key, rec in list(employee_date_records.items()):
        check_out = rec.get("check_out_time")
        if rec.get("check_in_time") or not check_out:
            continue
        record_date = rec.get("date") or key[1]
        if check_out.date() <= record_date or check_out.hour >= 12:
            continue
        next_key = (key[0], check_out.date())
        next_rec = employee_date_records.get(next_key)
        if not next_rec or next_rec.get("check_in_time") or not next_rec.get("check_out_time"):
            continue
        next_out = next_rec.get("check_out_time")
        if next_out.date() != check_out.date() or next_out.hour < 12:
            continue
        next_rec["check_in_time"] = check_out
        rec["check_out_time"] = None
        rec["force_public_leave"] = True
        repaired += 1
    return repaired

def parse_salary_draft_number(draft, field_names):
    if not draft or not draft.raw_data:
        return None
    try:
        raw = json.loads(draft.raw_data)
    except:
        return None
    normalized_targets = {normalize_header_text(name) for name in field_names}
    for key, value in raw.items():
        if normalize_header_text(key) in normalized_targets:
            text = str(value).strip()
            if not text or text.lower() == "nan":
                return None
            return parse_money(text)
    return None

def sum_salary_draft_numbers_by_keywords(draft, keywords):
    if not draft or not draft.raw_data:
        return 0
    try:
        raw = json.loads(draft.raw_data)
    except:
        return 0
    total = 0
    for key, value in raw.items():
        key_text = normalize_header_text(key)
        if any(keyword in key_text for keyword in keywords):
            total += parse_money(value)
    return total

def remark_has_any(remark, keywords):
    text = normalize_header_text(remark or "")
    return any(keyword in text for keyword in keywords)

def get_full_attendance_bonus(emp, salary_standard, is_full_attendance):
    if not is_full_attendance:
        return 0
    if salary_standard and (salary_standard.full_attendance_bonus or 0) > 0:
        return salary_standard.full_attendance_bonus or 0
    return emp.full_attendance_bonus or 0

def calculate_late_deduct(late_minutes, salary_rule):
    if not salary_rule or not salary_rule.late_deduct_tiers or late_minutes <= 0:
        return 0
    try:
        tiers = json.loads(salary_rule.late_deduct_tiers)
    except:
        return 0

    for tier in sorted(tiers, key=lambda x: float(x.get("min", 0))):
        tier_min = float(tier.get("min", 0))
        tier_max = float(tier.get("max", 0))
        if late_minutes >= tier_min and late_minutes <= tier_max:
            return float(tier.get("deduct", 0) or 0)

    open_ended = [t for t in tiers if float(t.get("max", 0) or 0) <= 0]
    if open_ended:
        return float(open_ended[-1].get("deduct", 0) or 0)

    sorted_tiers = sorted(tiers, key=lambda x: float(x.get("max", 0) or 0))
    if sorted_tiers and late_minutes > float(sorted_tiers[-1].get("max", 0) or 0):
        return float(sorted_tiers[-1].get("deduct", 0) or 0)
    return 0

def calculate_value_tier_deduct(value, tiers_text):
    if value <= 0 or not tiers_text:
        return 0
    try:
        tiers = json.loads(tiers_text)
    except:
        return 0
    for tier in sorted(tiers, key=lambda x: float(x.get("min", 0))):
        tier_min = float(tier.get("min", 0) or 0)
        tier_max = float(tier.get("max", 0) or 0)
        if value >= tier_min and (tier_max <= 0 or value <= tier_max):
            return float(tier.get("deduct", 0) or 0)
    return 0

def calculate_late_event_deduct(late_events, salary_rule):
    if not salary_rule:
        return 0
    event_total = sum(calculate_value_tier_deduct(minutes, salary_rule.late_deduct_tiers or "") for minutes in late_events)
    count_total = calculate_count_tier_deduct(len(late_events), getattr(salary_rule, "late_count_deduct_tiers", "") or "")
    return event_total + count_total

def calculate_count_tier_deduct(count, tiers_text):
    if count <= 0 or not tiers_text:
        return 0
    try:
        tiers = json.loads(tiers_text)
    except:
        return 0
    total = 0
    for tier in tiers:
        tier_min = int(float(tier.get("min", 0) or 0))
        tier_max = int(float(tier.get("max", 0) or 0))
        deduct = float(tier.get("deduct", 0) or 0)
        if tier_min <= 0:
            tier_min = 1
        upper = count if tier_max <= 0 else min(count, tier_max)
        if upper >= tier_min:
            total += (upper - tier_min + 1) * deduct
    return total

def calculate_threshold_penalty(count, tiers_text):
    if count <= 0 or not tiers_text:
        return 0
    try:
        tiers = json.loads(tiers_text)
    except:
        return 0
    total = 0
    for tier in tiers:
        tier_min = int(float(tier.get("min", 0) or 0))
        penalty = float(tier.get("deduct", tier.get("penalty", 0)) or 0)
        if tier_min > 0 and count >= tier_min:
            total += penalty
    return total

def iter_dates(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

def get_position_rules(db, emp):
    if not emp:
        return []
    return db.query(PositionAttendanceRule).filter(
        PositionAttendanceRule.store_id == emp.store_id,
        PositionAttendanceRule.position == emp.position,
        PositionAttendanceRule.is_active == True
    ).all()

def classify_manual_attendance(status, check_in_time=None, check_out_time=None):
    if status in ["公休", "病假", "事假", "事假两小时", "旷工", "离职"]:
        return status, status
    if not check_in_time and not check_out_time:
        return "上午缺卡", "下午缺卡"
    if not check_in_time:
        return "上午缺卡", "正常"
    if not check_out_time:
        return "正常", "下午缺卡"
    return "正常", "正常"

def result_minutes(result_text, prefix, stored_minutes=0):
    if stored_minutes and stored_minutes > 0:
        return int(stored_minutes)
    text = result_text or ""
    if not text.startswith(prefix):
        return 0
    import re
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0

def is_missing_result(result_text):
    text = result_text or ""
    return "缺卡" in text or "未打卡" in text

def is_late_result(result_text, late_minutes=0):
    return (late_minutes or 0) > 0 or (result_text or "").startswith("迟到")

def is_early_result(result_text, early_minutes=0):
    return (early_minutes or 0) > 0 or (result_text or "").startswith("早退")

def normalize_rule_time_value(value):
    if value is None:
        return ""
    try:
        import pandas as pd
        if pd.isna(value):
            return ""
    except:
        pass
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return f"{int(value.hour):02d}:{int(value.minute):02d}"
    text = str(value).strip().replace("：", ":")
    if not text or text.lower() == "nan":
        return ""
    if "次日" in text:
        text = text.replace("次日", "").strip()
    if " " in text:
        text = text.split(" ")[-1]
    if text.count(":") >= 1:
        parts = text.split(":")
        try:
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        except:
            return text
    return text

def validate_hhmm(time_text):
    import re
    if not re.match(r"^\d{1,2}:\d{2}$", time_text or ""):
        return False
    hour, minute = [int(x) for x in time_text.split(":")]
    return 0 <= hour <= 23 and 0 <= minute <= 59

def parse_required_float(value, field_name, row_number, min_value=0):
    try:
        if pd.isna(value):
            raise ValueError()
    except TypeError:
        pass
    try:
        number = float(str(value).strip())
    except:
        raise ValueError(f"行{row_number}: {field_name}必须是数字")
    if number < min_value:
        raise ValueError(f"行{row_number}: {field_name}不能小于{min_value}")
    return number

def validate_tiers(value, row_number, field_name, required_keys=("min", "max", "deduct"), allow_open_max=True):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raise ValueError(f"行{row_number}: {field_name}不能为空")
    text = str(value).strip()
    try:
        tiers = json.loads(text)
    except:
        raise ValueError(f"行{row_number}: {field_name}必须是JSON数组")
    if not isinstance(tiers, list) or not tiers:
        raise ValueError(f"行{row_number}: {field_name}必须至少包含一档")
    for index, tier in enumerate(tiers, start=1):
        if not isinstance(tier, dict):
            raise ValueError(f"行{row_number}: {field_name}第{index}档格式错误")
        for key in required_keys:
            if key not in tier:
                raise ValueError(f"行{row_number}: {field_name}第{index}档缺少{key}")
        tier_min = float(tier.get("min"))
        tier_max = float(tier.get("max", 0) or 0)
        tier_deduct = float(tier.get("deduct", tier.get("penalty", 0)))
        if tier_min < 0 or tier_max < 0 or tier_deduct < 0:
            raise ValueError(f"行{row_number}: {field_name}数值不能为负")
        if "max" in required_keys and tier_max <= 0 and not allow_open_max:
            raise ValueError(f"行{row_number}: {field_name}第{index}档max必须大于0")
        if tier_max > 0 and tier_max < tier_min:
            raise ValueError(f"行{row_number}: {field_name}max不能小于min")
    return json.dumps(tiers, ensure_ascii=False)

def validate_late_deduct_tiers(value, row_number):
    return validate_tiers(value, row_number, "迟到扣款档位")

def add_salary_audit(db, batch_id, rule_code, rule_name, severity, description, draft=None, employee=None):
    audit = SalaryAuditResult(
        batch_id=batch_id,
        draft_id=draft.id if draft else None,
        employee_id=employee.id if employee else (draft.employee_id if draft else None),
        rule_code=rule_code,
        rule_name=rule_name,
        severity=severity,
        description=description,
        status="pending"
    )
    db.add(audit)
    return audit

def get_employee_salary_standard(db, emp):
    if not emp:
        return None, "none"
    if (emp.base_salary or 0) > 0 or (emp.full_attendance_bonus or 0) > 0 or (emp.allowance or 0) > 0 or (emp.public_leave_days or 0) > 0:
        return {
            "base_salary": emp.base_salary or 0,
            "full_attendance_bonus": emp.full_attendance_bonus or 0,
            "allowance": emp.allowance or 0,
            "public_leave_days": emp.public_leave_days or 0,
            "standard_work_days": 0,
            "min_net_salary": 0,
            "max_net_salary": 0,
            "source_name": "员工个人工资标准",
        }, "employee"
    standard = db.query(SalaryStandard).filter(
        SalaryStandard.store_id == emp.store_id,
        SalaryStandard.position == emp.position,
        SalaryStandard.is_active == True
    ).first()
    if not standard:
        return None, "none"
    return {
        "base_salary": standard.base_salary or 0,
        "full_attendance_bonus": standard.full_attendance_bonus or 0,
        "allowance": standard.allowance or 0,
        "public_leave_days": standard.public_leave_days or 0,
        "standard_work_days": standard.standard_work_days or 0,
        "min_net_salary": standard.min_net_salary or 0,
        "max_net_salary": standard.max_net_salary or 0,
        "source_name": "店面岗位工资标准",
    }, "position"

def add_standard_mismatch_audits(db, batch_id, draft, emp, standard):
    tolerance = 0.01
    if abs((draft.base_salary or 0) - (standard["base_salary"] or 0)) > tolerance:
        add_salary_audit(db, batch_id, "BASE_SALARY_MISMATCH", "基本工资与标准不一致", "warning", f"{emp.name} 工资表基本工资 {draft.base_salary}，{standard['source_name']}为 {standard['base_salary']}", draft=draft, employee=emp)
    if standard["full_attendance_bonus"] and draft.full_attendance_bonus > standard["full_attendance_bonus"] + tolerance:
        add_salary_audit(db, batch_id, "FULL_BONUS_OVER_STANDARD", "满勤奖超过标准", "warning", f"{emp.name} 工资表满勤奖 {draft.full_attendance_bonus}，标准 {standard['full_attendance_bonus']}", draft=draft, employee=emp)
    if standard["allowance"] and abs((draft.allowance or 0) - standard["allowance"]) > tolerance:
        add_salary_audit(db, batch_id, "ALLOWANCE_MISMATCH", "补助与标准不一致", "info", f"{emp.name} 工资表补助 {draft.allowance}，标准 {standard['allowance']}", draft=draft, employee=emp)
    if standard["min_net_salary"] and draft.net_salary < standard["min_net_salary"] - tolerance:
        add_salary_audit(db, batch_id, "NET_BELOW_STANDARD_RANGE", "实发低于标准区间", "warning", f"{emp.name} 实发工资 {draft.net_salary}，低于标准下限 {standard['min_net_salary']}", draft=draft, employee=emp)
    if standard["max_net_salary"] and draft.net_salary > standard["max_net_salary"] + tolerance:
        add_salary_audit(db, batch_id, "NET_ABOVE_STANDARD_RANGE", "实发高于标准区间", "warning", f"{emp.name} 实发工资 {draft.net_salary}，高于标准上限 {standard['max_net_salary']}", draft=draft, employee=emp)

def pick_standard_value(values):
    nums = [round(float(v or 0), 2) for v in values if float(v or 0) > 0]
    if not nums:
        return 0
    counts = {}
    for value in nums:
        counts[value] = counts.get(value, 0) + 1
    max_count = max(counts.values())
    common_values = [value for value, count in counts.items() if count == max_count]
    if max_count > 1 or len(common_values) == 1:
        return common_values[0]
    nums.sort()
    mid = len(nums) // 2
    if len(nums) % 2:
        return nums[mid]
    return round((nums[mid - 1] + nums[mid]) / 2, 2)

def pick_standard_max(values):
    nums = [round(float(v or 0), 2) for v in values if float(v or 0) > 0]
    return max(nums) if nums else 0

def sync_salary_standards_from_employees(db, store_id=None):
    query = db.query(Employee).filter(
        Employee.is_active == True,
        Employee.status != "离职",
        Employee.position != None,
        Employee.position != ""
    )
    if store_id:
        query = query.filter(Employee.store_id == store_id)
    employees = query.all()

    grouped = {}
    for emp in employees:
        has_salary_data = any([
            (emp.base_salary or 0) > 0,
            (emp.full_attendance_bonus or 0) > 0,
            (emp.allowance or 0) > 0,
            (emp.public_leave_days or 0) > 0
        ])
        if not has_salary_data:
            continue
        key = (emp.store_id, (emp.position or "").strip())
        grouped.setdefault(key, []).append(emp)

    synced = 0
    with_differences = 0
    for (group_store_id, position), group in grouped.items():
        if not group_store_id or not position:
            continue

        base_values = [emp.base_salary or 0 for emp in group]
        bonus_values = [emp.full_attendance_bonus or 0 for emp in group]
        allowance_values = [emp.allowance or 0 for emp in group]
        leave_values = [emp.public_leave_days or 0 for emp in group]
        distinct_base_values = sorted({round(float(v or 0), 2) for v in base_values if float(v or 0) > 0})
        has_difference = len(distinct_base_values) > 1
        if has_difference:
            with_differences += 1

        standards = db.query(SalaryStandard).filter(
            SalaryStandard.store_id == group_store_id,
            SalaryStandard.position == position,
            SalaryStandard.is_active == True
        ).order_by(SalaryStandard.id).all()
        if standards:
            standard = standards[0]
            for duplicate in standards[1:]:
                duplicate.is_active = False
                duplicate.description = "重复岗位标准，已由员工工资信息生成时停用"
        else:
            standard = SalaryStandard(store_id=group_store_id, position=position)
            db.add(standard)

        standard.base_salary = pick_standard_value(base_values)
        standard.full_attendance_bonus = pick_standard_max(bonus_values)
        standard.allowance = pick_standard_max(allowance_values)
        standard.public_leave_days = pick_standard_max(leave_values)
        standard.description = f"由员工工资信息生成；样本{len(group)}人"
        if has_difference:
            standard.description += f"；同岗基本工资存在差异: {', '.join(str(v) for v in distinct_base_values[:6])}"
        standard.is_active = True
        synced += 1

    return synced, with_differences

def run_salary_audit(db, batch_id):
    batch = db.query(SalaryImportBatch).filter(SalaryImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="工资批次不存在")

    db.query(SalaryAuditResult).filter(SalaryAuditResult.batch_id == batch_id).delete()
    drafts = db.query(SalaryDraft).filter(SalaryDraft.batch_id == batch_id).all()
    start, end = month_range(batch.year, batch.month)

    draft_by_employee = {d.employee_id: d for d in drafts if d.employee_id}
    name_counts = {}
    for d in drafts:
        key = d.employee_name.strip()
        name_counts[key] = name_counts.get(key, 0) + 1
        if not d.employee_id:
            add_salary_audit(db, batch_id, "UNKNOWN_EMPLOYEE", "工资表员工不在档案", "critical", f"工资表中的 {d.employee_name} 未匹配到员工档案", draft=d)
        if d.net_salary <= 0:
            add_salary_audit(db, batch_id, "NON_POSITIVE_NET", "实发工资为0或负数", "critical", f"{d.employee_name} 实发工资为 {d.net_salary}", draft=d)
        if d.raw_employee_id and d.employee and d.raw_employee_id != d.employee.employee_id:
            add_salary_audit(db, batch_id, "EMPLOYEE_ID_MISMATCH", "工号不匹配", "critical", f"{d.employee_name} 工资表工号 {d.raw_employee_id} 与档案工号 {d.employee.employee_id} 不一致", draft=d, employee=d.employee)
        if d.raw_id_card and d.employee and d.employee.id_card and d.raw_id_card != d.employee.id_card:
            add_salary_audit(db, batch_id, "ID_CARD_MISMATCH", "身份证不匹配", "critical", f"{d.employee_name} 工资表身份证与档案身份证不一致", draft=d, employee=d.employee)

    for name, count in name_counts.items():
        if count > 1:
            for d in [x for x in drafts if x.employee_name.strip() == name]:
                add_salary_audit(db, batch_id, "DUPLICATE_NAME", "工资表同名重复", "critical", f"工资表中 {name} 出现 {count} 次", draft=d)

    emp_query = db.query(Employee)
    if batch.store_id:
        emp_query = emp_query.filter(Employee.store_id == batch.store_id)
    employees = emp_query.all()

    for emp in employees:
        draft = draft_by_employee.get(emp.id)
        if emp.is_active and emp.status != "离职" and not draft:
            add_salary_audit(db, batch_id, "ACTIVE_EMPLOYEE_MISSING", "在职员工未出现在工资表", "critical", f"{emp.name} 为在职员工，但本月工资表没有记录", employee=emp)
            continue
        if not draft:
            continue

        standard, standard_source = get_employee_salary_standard(db, emp)
        if not standard:
            add_salary_audit(db, batch_id, "MISSING_SALARY_STANDARD", "缺少工资标准", "warning", f"{emp.name} 未维护员工个人工资标准，也未维护 {emp.store.name if emp.store else ''}/{emp.position} 的岗位工资标准", draft=draft, employee=emp)
        else:
            add_standard_mismatch_audits(db, batch_id, draft, emp, standard)

        att = summarize_employee_attendance(db, emp.id, batch.year, batch.month)
        salary_standard = get_salary_standard_record(db, emp)
        salary_rule = db.query(SalaryRule).filter(SalaryRule.store_id == emp.store_id, SalaryRule.is_active == True).first()
        calendar_days = monthrange(batch.year, batch.month)[1]
        is_full_attendance, full_attendance_checks = evaluate_full_attendance(att, salary_standard, calendar_days, salary_rule, emp, batch.year, batch.month)
        total_deduction = draft.deduction or 0
        has_deduction_or_remark = total_deduction > 0 or bool((draft.remark or "").strip())
        late_related_deduct = sum_salary_draft_numbers_by_keywords(draft, ["迟到", "早退"])
        missing_related_deduct = sum_salary_draft_numbers_by_keywords(draft, ["未打卡", "缺卡", "漏打卡"])
        has_late_deduct_or_remark = late_related_deduct > 0 or remark_has_any(draft.remark, ["迟到", "早退"])
        has_missing_deduct_or_remark = missing_related_deduct > 0 or remark_has_any(draft.remark, ["未打卡", "缺卡", "漏打卡"])

        if (emp.status == "离职" or not emp.is_active or att["is_resigned"]) and draft.net_salary > 0:
            add_salary_audit(db, batch_id, "RESIGNED_WITH_SALARY", "离职员工仍有工资", "critical", f"{emp.name} 已离职或考勤标记离职，但实发工资 {draft.net_salary}", draft=draft, employee=emp)
        effective_hire_date = get_effective_hire_date(emp)
        if effective_hire_date and effective_hire_date > end and draft.net_salary > 0:
            add_salary_audit(db, batch_id, "HIRED_AFTER_MONTH", "入职晚于工资月份", "critical", f"{emp.name} 入职日期 {effective_hire_date} 晚于工资月份，但有工资 {draft.net_salary}", draft=draft, employee=emp)
        if att["absent_days"] > 0 and not has_deduction_or_remark:
            add_salary_audit(db, batch_id, "ABSENT_NO_DEDUCTION", "旷工无扣款或备注", "critical", f"{emp.name} 本月旷工 {att['absent_days']} 天，工资表无扣款/备注", draft=draft, employee=emp)
        if att["personal_leave_days"] > 0 and not has_deduction_or_remark:
            add_salary_audit(db, batch_id, "LEAVE_NO_DEDUCTION", "事假无扣款或备注", "warning", f"{emp.name} 事假 {att['personal_leave_days']} 天，工资表无扣款/备注", draft=draft, employee=emp)
        if att["personal_leave_2h_count"] > 0 and not has_deduction_or_remark:
            add_salary_audit(db, batch_id, "PERSONAL_LEAVE_2H_NO_DEDUCTION", "事假两小时无扣款或备注", "warning", f"{emp.name} 事假两小时 {att['personal_leave_2h_count']} 次，工资表无扣款/备注", draft=draft, employee=emp)
        if (att["late_minutes"] > 0 or att["early_leave_minutes"] > 0) and not has_late_deduct_or_remark:
            add_salary_audit(db, batch_id, "LATE_EARLY_NO_DEDUCTION", "迟到早退无扣款或备注", "warning", f"{emp.name} 迟到 {att['late_minutes']} 分钟、早退 {att['early_leave_minutes']} 分钟，工资表无迟到/早退扣款或备注", draft=draft, employee=emp)
        if att["missing_count"] > 0 and not has_missing_deduct_or_remark:
            add_salary_audit(db, batch_id, "MISSING_NO_DEDUCTION", "未打卡无扣款或备注", "warning", f"{emp.name} 未打卡/缺卡 {att['missing_count']} 次，工资表无未打卡/缺卡扣款或备注", draft=draft, employee=emp)
        should_rest_days_for_audit = get_standard_rest_days(emp, salary_standard)
        if att["public_leave_days"] > should_rest_days_for_audit + 0.01:
            add_salary_audit(db, batch_id, "PUBLIC_LEAVE_OVER_STANDARD", "公休超过应公休", "warning", f"{emp.name} 已公休 {att['public_leave_days']} 天，应公休 {should_rest_days_for_audit} 天，超出 {round(att['public_leave_days'] - should_rest_days_for_audit, 2)} 天", draft=draft, employee=emp)
        if att["missing_count"] >= 3 and draft.full_attendance_bonus > 0:
            add_salary_audit(db, batch_id, "MISSING_WITH_FULL_BONUS", "缺卡较多仍发满勤", "warning", f"{emp.name} 缺卡/待确认 {att['missing_count']} 次，但满勤奖 {draft.full_attendance_bonus}", draft=draft, employee=emp)
        if not is_full_attendance and draft.full_attendance_bonus > 0:
            failed_items = [name for name, ok in full_attendance_checks.items() if not ok]
            add_salary_audit(db, batch_id, "NOT_FULL_ATTENDANCE_BONUS", "未满勤但发满勤奖", "warning", f"{emp.name} 未满足满勤规则({', '.join(failed_items)})，但满勤奖 {draft.full_attendance_bonus}", draft=draft, employee=emp)

        draft_work_days = parse_salary_draft_number(draft, ["出勤天数", "开工资天数", "计薪天数", "工资天数"])
        attendance_with_taken_rest = round((att.get("normal_days", 0) or 0) + (att.get("public_leave_days", 0) or 0), 2)
        if draft_work_days is not None and draft_work_days > attendance_with_taken_rest + 0.01:
            add_salary_audit(
                db,
                batch_id,
                "WORK_DAYS_OVER_ATTENDANCE",
                "开工资天数超过考勤",
                "warning",
                f"{emp.name} 工资表开工资天数 {draft_work_days}，实际出勤+已公休为 {attendance_with_taken_rest}；未休公休应另按加班核算",
                draft=draft,
                employee=emp
            )

        if standard:
            payable_days, overtime_days, employment_days, should_rest_days, is_partial_month = calculate_payable_days(emp, att, salary_standard, batch.year, batch.month)
            monthly_fixed_salary = (standard["base_salary"] or 0) + (standard["allowance"] or 0) + (emp.seniority_bonus or 0)
            expected_regular_salary = monthly_fixed_salary * (payable_days / calendar_days) if calendar_days else 0
            expected_full_bonus = (standard["full_attendance_bonus"] or 0) if is_full_attendance else 0
            expected_salary_upper = expected_regular_salary + expected_full_bonus + overtime_days * ((standard["base_salary"] or 0) / calendar_days if calendar_days else 0)
            if is_partial_month and draft.net_salary > expected_salary_upper + 30:
                add_salary_audit(
                    db,
                    batch_id,
                    "PARTIAL_MONTH_SALARY_OVERPAID",
                    "入职当月工资偏高",
                    "warning",
                    f"{emp.name} 入职当月应按 {payable_days}/{calendar_days} 天核算，估算应发上限 {round(expected_salary_upper, 2)}，工资表实发 {draft.net_salary}",
                    draft=draft,
                    employee=emp
                )

        prev_year = batch.year if batch.month > 1 else batch.year - 1
        prev_month = batch.month - 1 if batch.month > 1 else 12
        prev = db.query(SalaryDraft).join(SalaryImportBatch, SalaryDraft.batch_id == SalaryImportBatch.id).filter(
            SalaryDraft.employee_id == emp.id,
            SalaryImportBatch.year == prev_year,
            SalaryImportBatch.month == prev_month
        ).order_by(SalaryDraft.id.desc()).first()
        if prev and prev.net_salary > 0:
            change_rate = abs(draft.net_salary - prev.net_salary) / prev.net_salary
            if change_rate > 0.3:
                add_salary_audit(db, batch_id, "SALARY_CHANGE_OVER_30", "实发工资环比波动超过30%", "warning", f"{emp.name} 上月 {prev.net_salary}，本月 {draft.net_salary}，波动 {round(change_rate * 100, 1)}%", draft=draft, employee=emp)

    grouped = {}
    for d in drafts:
        key = (d.store_name or (d.employee.store.name if d.employee and d.employee.store else ""), d.position or (d.employee.position if d.employee else ""))
        grouped.setdefault(key, []).append(d)
    for (store_name, position), items in grouped.items():
        salaries = [x.net_salary for x in items if x.net_salary > 0]
        if len(salaries) < 3:
            continue
        avg_salary = sum(salaries) / len(salaries)
        for d in items:
            if avg_salary > 0 and d.net_salary > 0 and abs(d.net_salary - avg_salary) / avg_salary > 0.5:
                add_salary_audit(db, batch_id, "POSITION_SALARY_OUTLIER", "同店同岗工资差异过大", "info", f"{d.employee_name} 实发 {d.net_salary}，{store_name}/{position} 平均 {round(avg_salary, 2)}", draft=d, employee=d.employee)

    current_total = batch.total_net_salary or 0
    prev_year = batch.year if batch.month > 1 else batch.year - 1
    prev_month = batch.month - 1 if batch.month > 1 else 12
    prev_batch_query = db.query(SalaryImportBatch).filter(
        SalaryImportBatch.year == prev_year,
        SalaryImportBatch.month == prev_month
    )
    if batch.store_id:
        prev_batch_query = prev_batch_query.filter(SalaryImportBatch.store_id == batch.store_id)
    prev_total = sum([b.total_net_salary or 0 for b in prev_batch_query.all()])
    if prev_total > 0 and current_total > 0:
        change_rate = abs(current_total - prev_total) / prev_total
        if change_rate > 0.3:
            add_salary_audit(db, batch_id, "STORE_TOTAL_CHANGE", "店面工资总额环比异常", "warning", f"上月总额 {round(prev_total, 2)}，本月总额 {round(current_total, 2)}，波动 {round(change_rate * 100, 1)}%")

    db.commit()
    return db.query(SalaryAuditResult).filter(SalaryAuditResult.batch_id == batch_id).count()

@app.get("/api/salary-rules", response_model=List[dict])
def get_salary_rules(store_id: int = None, db: Session = Depends(get_db)):
    query = db.query(SalaryRule).filter(SalaryRule.is_active == True)
    if store_id:
        query = query.filter(SalaryRule.store_id == store_id)
    rules = query.all()
    result = []
    for r in rules:
        store = db.query(Store).filter(Store.id == r.store_id).first()
        result.append({
            "id": r.id, "store_id": r.store_id,
            "store_name": store.name if store else "",
            "late_deduct_tiers": r.late_deduct_tiers,
            "late_count_deduct_tiers": getattr(r, "late_count_deduct_tiers", "") or "",
            "missing_deduct_tiers": getattr(r, "missing_deduct_tiers", "") or "",
            "late_count_penalty_tiers": getattr(r, "late_count_penalty_tiers", "") or "",
            "early_leave_deduct_per_minute": r.early_leave_deduct_per_minute,
            "absent_multiplier": r.absent_multiplier,
            "absent_extra_penalty": getattr(r, "absent_extra_penalty", 0) or 0,
            "sick_leave_deduct_per_day": 0,
            "personal_leave_deduct_per_day": r.personal_leave_deduct_per_day,
            "personal_leave_2h_deduct": getattr(r, "personal_leave_2h_deduct", 0) or 0,
            "missing_check_deduct": getattr(r, "missing_check_deduct", 0) or 0,
            "allow_late_count": getattr(r, "allow_late_count", 0) or 0,
            "allow_abnormal_count": getattr(r, "allow_abnormal_count", 0) or 0,
            "allow_late_minutes": getattr(r, "allow_late_minutes", 0) or 0,
            "allow_early_leave_minutes": getattr(r, "allow_early_leave_minutes", 0) or 0,
            "allow_sick_leave_days": getattr(r, "allow_sick_leave_days", 0) or 0,
            "allow_personal_leave_days": getattr(r, "allow_personal_leave_days", 0) or 0,
            "allow_personal_leave_2h_count": getattr(r, "allow_personal_leave_2h_count", 0) or 0,
            "allow_missing_count": getattr(r, "allow_missing_count", 0) or 0,
            "allow_absent_days": getattr(r, "allow_absent_days", 0) or 0,
            "is_active": r.is_active
        })
    return result

@app.post("/api/salary-rules")
def create_salary_rule(data: SalaryRuleCreate, db: Session = Depends(get_db)):
    rule = db.query(SalaryRule).filter(
        SalaryRule.store_id == data.store_id,
        SalaryRule.is_active == True
    ).order_by(SalaryRule.id).first()
    if not rule:
        rule = SalaryRule(store_id=data.store_id, is_active=True)
        db.add(rule)
    rule.late_deduct_tiers = data.late_deduct_tiers
    rule.late_count_deduct_tiers = data.late_count_deduct_tiers
    rule.missing_deduct_tiers = data.missing_deduct_tiers
    rule.late_count_penalty_tiers = data.late_count_penalty_tiers
    rule.early_leave_deduct_per_minute = data.early_leave_deduct_per_minute
    rule.absent_multiplier = data.absent_multiplier
    rule.absent_extra_penalty = data.absent_extra_penalty
    rule.sick_leave_deduct_per_day = data.sick_leave_deduct_per_day
    rule.personal_leave_deduct_per_day = data.personal_leave_deduct_per_day
    rule.personal_leave_2h_deduct = data.personal_leave_2h_deduct
    rule.missing_check_deduct = data.missing_check_deduct
    rule.allow_late_count = data.allow_late_count
    rule.allow_abnormal_count = data.allow_abnormal_count
    rule.allow_late_minutes = data.allow_late_minutes
    rule.allow_early_leave_minutes = data.allow_early_leave_minutes
    rule.allow_sick_leave_days = data.allow_sick_leave_days
    rule.allow_personal_leave_days = data.allow_personal_leave_days
    rule.allow_personal_leave_2h_count = data.allow_personal_leave_2h_count
    rule.allow_missing_count = data.allow_missing_count
    rule.allow_absent_days = data.allow_absent_days
    rule.updated_at = datetime.now()
    db.commit()
    return {"message": "薪资规则已保存", "id": rule.id}

@app.post("/api/salary-rules/import")
async def import_salary_rules(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        df.columns = [normalize_header_text(col) for col in df.columns]
        df = df.loc[:, [c for c in df.columns if c and not str(c).startswith("未命名") and not str(c).startswith("Unnamed")]]

        required_columns = [
            "店面ID",
            "迟到扣款档位",
            "迟到次数扣款档位",
            "未打卡扣款档位",
            "迟到次数额外扣款档位",
            "早退扣款(元/分钟)",
            "旷工扣款倍数",
            "旷工固定罚款(元)",
            "病假扣款倍数",
            "事假扣款倍数",
            "事假2小时扣款(元)",
            "未打卡扣款(元/次)",
            "满勤允许迟到次数",
            "满勤允许异常合计次数",
            "满勤允许迟到分钟",
            "满勤允许早退分钟",
            "满勤允许病假天数",
            "满勤允许事假天数",
            "满勤允许事假2小时次数",
            "满勤允许未打卡次数",
            "满勤允许旷工天数",
        ]
        allowed_columns = set(required_columns + ["店面名称"])
        missing_columns = [c for c in required_columns if c not in df.columns]
        extra_columns = [c for c in df.columns if c not in allowed_columns]
        if missing_columns:
            raise HTTPException(status_code=400, detail=f"工资规则表缺少固定字段: {', '.join(missing_columns)}。请下载固定模板后填写")
        if extra_columns:
            raise HTTPException(status_code=400, detail=f"工资规则表包含不支持的字段: {', '.join(extra_columns)}。请只保留固定模板字段")
        
        imported = 0
        skipped = 0
        skipped_details = []
        
        for idx, row in df.iterrows():
            row_number = idx + 2
            store_id = row.get('店面ID') or row.get('store_id')
            if pd.isna(store_id):
                skipped += 1
                skipped_details.append(f"行{row_number}: 店面ID不能为空")
                continue

            try:
                store_id = int(float(store_id))
            except:
                skipped += 1
                skipped_details.append(f"行{row_number}: 店面ID必须是数字")
                continue

            store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
            if not store:
                skipped += 1
                skipped_details.append(f"行{row_number}: 店面ID {store_id} 不存在或已停用")
                continue

            try:
                late_tiers = validate_late_deduct_tiers(row.get("迟到扣款档位"), row_number)
                late_count_deduct_tiers = validate_tiers(row.get("迟到次数扣款档位"), row_number, "迟到次数扣款档位")
                missing_tiers = validate_tiers(row.get("未打卡扣款档位"), row_number, "未打卡扣款档位")
                late_count_tiers = validate_tiers(row.get("迟到次数额外扣款档位"), row_number, "迟到次数额外扣款档位", required_keys=("min", "deduct"))
                early_leave_deduct = parse_required_float(row.get("早退扣款(元/分钟)"), "早退扣款(元/分钟)", row_number)
                absent_multiplier = parse_required_float(row.get("旷工扣款倍数"), "旷工扣款倍数", row_number)
                absent_extra_penalty = parse_required_float(row.get("旷工固定罚款(元)"), "旷工固定罚款(元)", row_number)
                sick_leave_deduct = parse_required_float(row.get("病假扣款倍数"), "病假扣款倍数", row_number)
                personal_leave_deduct = parse_required_float(row.get("事假扣款倍数"), "事假扣款倍数", row_number)
                personal_leave_2h_deduct = parse_required_float(row.get("事假2小时扣款(元)"), "事假2小时扣款(元)", row_number)
                missing_check_deduct = parse_required_float(row.get("未打卡扣款(元/次)"), "未打卡扣款(元/次)", row_number)
                allow_late_count = int(parse_required_float(row.get("满勤允许迟到次数"), "满勤允许迟到次数", row_number))
                allow_abnormal_count = int(parse_required_float(row.get("满勤允许异常合计次数"), "满勤允许异常合计次数", row_number))
                allow_late_minutes = parse_required_float(row.get("满勤允许迟到分钟"), "满勤允许迟到分钟", row_number)
                allow_early_leave_minutes = parse_required_float(row.get("满勤允许早退分钟"), "满勤允许早退分钟", row_number)
                allow_sick_leave_days = parse_required_float(row.get("满勤允许病假天数"), "满勤允许病假天数", row_number)
                allow_personal_leave_days = parse_required_float(row.get("满勤允许事假天数"), "满勤允许事假天数", row_number)
                allow_personal_leave_2h_count = int(parse_required_float(row.get("满勤允许事假2小时次数"), "满勤允许事假2小时次数", row_number))
                allow_missing_count = int(parse_required_float(row.get("满勤允许未打卡次数"), "满勤允许未打卡次数", row_number))
                allow_absent_days = parse_required_float(row.get("满勤允许旷工天数"), "满勤允许旷工天数", row_number)
            except ValueError as e:
                skipped += 1
                skipped_details.append(str(e))
                continue
            
            existing = db.query(SalaryRule).filter(
                SalaryRule.store_id == store_id,
                SalaryRule.is_active == True
            ).first()
            
            if existing:
                existing.late_deduct_tiers = late_tiers
                existing.late_count_deduct_tiers = late_count_deduct_tiers
                existing.missing_deduct_tiers = missing_tiers
                existing.late_count_penalty_tiers = late_count_tiers
                existing.early_leave_deduct_per_minute = early_leave_deduct
                existing.absent_multiplier = absent_multiplier
                existing.absent_extra_penalty = absent_extra_penalty
                existing.sick_leave_deduct_per_day = sick_leave_deduct
                existing.personal_leave_deduct_per_day = personal_leave_deduct
                existing.personal_leave_2h_deduct = personal_leave_2h_deduct
                existing.missing_check_deduct = missing_check_deduct
                existing.allow_late_count = allow_late_count
                existing.allow_abnormal_count = allow_abnormal_count
                existing.allow_late_minutes = allow_late_minutes
                existing.allow_early_leave_minutes = allow_early_leave_minutes
                existing.allow_sick_leave_days = allow_sick_leave_days
                existing.allow_personal_leave_days = allow_personal_leave_days
                existing.allow_personal_leave_2h_count = allow_personal_leave_2h_count
                existing.allow_missing_count = allow_missing_count
                existing.allow_absent_days = allow_absent_days
                existing.updated_at = datetime.now()
            else:
                rule = SalaryRule(
                    store_id=store_id,
                    late_deduct_tiers=late_tiers,
                    late_count_deduct_tiers=late_count_deduct_tiers,
                    missing_deduct_tiers=missing_tiers,
                    late_count_penalty_tiers=late_count_tiers,
                    early_leave_deduct_per_minute=early_leave_deduct,
                    absent_multiplier=absent_multiplier,
                    absent_extra_penalty=absent_extra_penalty,
                    sick_leave_deduct_per_day=sick_leave_deduct,
                    personal_leave_deduct_per_day=personal_leave_deduct,
                    personal_leave_2h_deduct=personal_leave_2h_deduct,
                    missing_check_deduct=missing_check_deduct,
                    allow_late_count=allow_late_count,
                    allow_abnormal_count=allow_abnormal_count,
                    allow_late_minutes=allow_late_minutes,
                    allow_early_leave_minutes=allow_early_leave_minutes,
                    allow_sick_leave_days=allow_sick_leave_days,
                    allow_personal_leave_days=allow_personal_leave_days,
                    allow_personal_leave_2h_count=allow_personal_leave_2h_count,
                    allow_missing_count=allow_missing_count,
                    allow_absent_days=allow_absent_days
                )
                db.add(rule)
            imported += 1
        
        db.commit()
        return {"message": "导入完成", "imported": imported, "skipped": skipped, "skip_details": "；".join(skipped_details[:20])}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

@app.get("/api/salary-rules/template")
def download_salary_rules_template(store_id: int = None, db: Session = Depends(get_db)):
    stores_query = db.query(Store).filter(Store.is_active == True)
    if store_id:
        stores_query = stores_query.filter(Store.id == store_id)
    stores = stores_query.order_by(Store.code).all()
    if store_id and not stores:
        raise HTTPException(status_code=404, detail="店面不存在")

    rows = []
    default_tiers = json.dumps([{"min": 0, "max": 10, "deduct": 20}, {"min": 10, "max": 60, "deduct": 120}], ensure_ascii=False)
    default_late_count_deduct_tiers = json.dumps([{"min": 1, "max": 0, "deduct": 0}], ensure_ascii=False)
    default_missing_tiers = json.dumps([{"min": 1, "max": 0, "deduct": 10}], ensure_ascii=False)
    default_late_count_tiers = json.dumps([{"min": 6, "deduct": 100}], ensure_ascii=False)
    for store in stores:
        rule = db.query(SalaryRule).filter(SalaryRule.store_id == store.id, SalaryRule.is_active == True).first()
        rows.append({
            "店面ID": store.id,
            "店面名称": store.name,
            "迟到扣款档位": rule.late_deduct_tiers if rule and rule.late_deduct_tiers else default_tiers,
            "迟到次数扣款档位": getattr(rule, "late_count_deduct_tiers", "") if rule and getattr(rule, "late_count_deduct_tiers", "") else default_late_count_deduct_tiers,
            "未打卡扣款档位": getattr(rule, "missing_deduct_tiers", "") if rule and getattr(rule, "missing_deduct_tiers", "") else default_missing_tiers,
            "迟到次数额外扣款档位": getattr(rule, "late_count_penalty_tiers", "") if rule and getattr(rule, "late_count_penalty_tiers", "") else default_late_count_tiers,
            "早退扣款(元/分钟)": rule.early_leave_deduct_per_minute if rule else 0,
            "旷工扣款倍数": rule.absent_multiplier if rule else 2,
            "旷工固定罚款(元)": getattr(rule, "absent_extra_penalty", 0) if rule else 0,
            "病假扣款倍数": 0,
            "事假扣款倍数": rule.personal_leave_deduct_per_day if rule else 2,
            "事假2小时扣款(元)": getattr(rule, "personal_leave_2h_deduct", 0) if rule else 0,
            "未打卡扣款(元/次)": getattr(rule, "missing_check_deduct", 0) if rule else 0,
            "满勤允许迟到次数": getattr(rule, "allow_late_count", 0) if rule else 3,
            "满勤允许异常合计次数": getattr(rule, "allow_abnormal_count", 0) if rule else 0,
            "满勤允许迟到分钟": getattr(rule, "allow_late_minutes", 0) if rule else 0,
            "满勤允许早退分钟": getattr(rule, "allow_early_leave_minutes", 0) if rule else 0,
            "满勤允许病假天数": getattr(rule, "allow_sick_leave_days", 0) if rule else 0,
            "满勤允许事假天数": getattr(rule, "allow_personal_leave_days", 0) if rule else 0,
            "满勤允许事假2小时次数": getattr(rule, "allow_personal_leave_2h_count", 0) if rule else 0,
            "满勤允许未打卡次数": getattr(rule, "allow_missing_count", 0) if rule else 0,
            "满勤允许旷工天数": getattr(rule, "allow_absent_days", 0) if rule else 0,
        })

    df = pd.DataFrame(rows, columns=[
        "店面ID",
        "店面名称",
        "迟到扣款档位",
        "迟到次数扣款档位",
        "未打卡扣款档位",
        "迟到次数额外扣款档位",
        "早退扣款(元/分钟)",
        "旷工扣款倍数",
        "旷工固定罚款(元)",
        "病假扣款倍数",
        "事假扣款倍数",
        "事假2小时扣款(元)",
        "未打卡扣款(元/次)",
        "满勤允许迟到次数",
        "满勤允许异常合计次数",
        "满勤允许迟到分钟",
        "满勤允许早退分钟",
        "满勤允许病假天数",
        "满勤允许事假天数",
        "满勤允许事假2小时次数",
        "满勤允许未打卡次数",
        "满勤允许旷工天数",
    ])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='工资规则模板')
    output.seek(0)

    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=salary_rule_template.xlsx; filename*=UTF-8''%E5%B7%A5%E8%B5%84%E8%A7%84%E5%88%99%E5%9B%BA%E5%AE%9A%E6%A8%A1%E6%9D%BF.xlsx"}
    )

@app.get("/api/salary-rules/export")
def export_salary_rules(store_id: int = None, db: Session = Depends(get_db)):
    query = db.query(SalaryRule).filter(SalaryRule.is_active == True)
    if store_id:
        query = query.filter(SalaryRule.store_id == store_id)
    rules = query.all()
    
    data = []
    for r in rules:
        store = db.query(Store).filter(Store.id == r.store_id).first()
        data.append({
            "店面ID": r.store_id,
            "店面名称": store.name if store else "",
            "迟到扣款档位": r.late_deduct_tiers or "",
            "迟到次数扣款档位": getattr(r, "late_count_deduct_tiers", "") or "",
            "未打卡扣款档位": getattr(r, "missing_deduct_tiers", "") or "",
            "迟到次数额外扣款档位": getattr(r, "late_count_penalty_tiers", "") or "",
            "早退扣款(元/分钟)": r.early_leave_deduct_per_minute or 0,
            "旷工扣款倍数": r.absent_multiplier or 2,
            "旷工固定罚款(元)": getattr(r, "absent_extra_penalty", 0) or 0,
            "病假扣款倍数": 0,
            "事假扣款倍数": r.personal_leave_deduct_per_day or 2,
            "事假2小时扣款(元)": getattr(r, "personal_leave_2h_deduct", 0) or 0,
            "未打卡扣款(元/次)": getattr(r, "missing_check_deduct", 0) or 0,
            "满勤允许迟到次数": getattr(r, "allow_late_count", 0) or 0,
            "满勤允许异常合计次数": getattr(r, "allow_abnormal_count", 0) or 0,
            "满勤允许迟到分钟": getattr(r, "allow_late_minutes", 0) or 0,
            "满勤允许早退分钟": getattr(r, "allow_early_leave_minutes", 0) or 0,
            "满勤允许病假天数": getattr(r, "allow_sick_leave_days", 0) or 0,
            "满勤允许事假天数": getattr(r, "allow_personal_leave_days", 0) or 0,
            "满勤允许事假2小时次数": getattr(r, "allow_personal_leave_2h_count", 0) or 0,
            "满勤允许未打卡次数": getattr(r, "allow_missing_count", 0) or 0,
            "满勤允许旷工天数": getattr(r, "allow_absent_days", 0) or 0
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='工资规则')
    output.seek(0)
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=salary_rules.xlsx; filename*=UTF-8''%E5%B7%A5%E8%B5%84%E8%A7%84%E5%88%99%E6%A8%A1%E6%9D%BF.xlsx"}
    )

@app.get("/api/salary-standards")
def get_salary_standards(store_id: int = None, position: str = None, db: Session = Depends(get_db)):
    query = db.query(SalaryStandard).filter(SalaryStandard.is_active == True)
    if store_id:
        query = query.filter(SalaryStandard.store_id == store_id)
    if position:
        query = query.filter(SalaryStandard.position.contains(position))
    standards = query.order_by(SalaryStandard.store_id, SalaryStandard.position).all()
    return [{
        "id": s.id,
        "store_id": s.store_id,
        "store_name": s.store.name if s.store else "",
        "position": s.position,
        "base_salary": s.base_salary or 0,
        "full_attendance_bonus": s.full_attendance_bonus or 0,
        "allowance": s.allowance or 0,
        "public_leave_days": s.public_leave_days or 0,
        "standard_work_days": s.standard_work_days or 0,
        "min_net_salary": s.min_net_salary or 0,
        "max_net_salary": s.max_net_salary or 0,
        # 满勤判断标准
        "allow_late_minutes": getattr(s, "allow_late_minutes", 0) or 0,
        "allow_early_leave_minutes": getattr(s, "allow_early_leave_minutes", 0) or 0,
        "allow_sick_leave_days": getattr(s, "allow_sick_leave_days", 0) or 0,
        "allow_personal_leave_days": getattr(s, "allow_personal_leave_days", 0) or 0,
        "allow_personal_leave_2h_count": getattr(s, "allow_personal_leave_2h_count", 0) or 0,
        "allow_missing_count": getattr(s, "allow_missing_count", 0) or 0,
        "allow_absent_days": getattr(s, "allow_absent_days", 0) or 0,
        "description": s.description or "",
        "updated_at": s.updated_at.strftime("%Y-%m-%d %H:%M:%S") if s.updated_at else ""
    } for s in standards]

@app.post("/api/salary-standards")
def create_salary_standard(data: SalaryStandardCreate, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == data.store_id, Store.is_active == True).first()
    if not store:
        raise HTTPException(status_code=404, detail="店面不存在")
    standard = db.query(SalaryStandard).filter(
        SalaryStandard.store_id == data.store_id,
        SalaryStandard.position == data.position,
        SalaryStandard.is_active == True
    ).first()
    if not standard:
        standard = SalaryStandard(store_id=data.store_id, position=data.position)
        db.add(standard)
    standard.base_salary = data.base_salary
    standard.full_attendance_bonus = data.full_attendance_bonus
    standard.allowance = data.allowance
    standard.public_leave_days = data.public_leave_days
    standard.standard_work_days = data.standard_work_days
    standard.min_net_salary = data.min_net_salary
    standard.max_net_salary = data.max_net_salary
    # 满勤判断标准
    standard.allow_late_minutes = data.allow_late_minutes
    standard.allow_early_leave_minutes = data.allow_early_leave_minutes
    standard.allow_sick_leave_days = data.allow_sick_leave_days
    standard.allow_personal_leave_days = data.allow_personal_leave_days
    standard.allow_personal_leave_2h_count = data.allow_personal_leave_2h_count
    standard.allow_missing_count = data.allow_missing_count
    standard.allow_absent_days = data.allow_absent_days
    standard.description = data.description
    standard.is_active = True
    log_operation(db, "系统", "保存", "工资标准", standard.id, f"{store.name}-{standard.position}", "保存店面岗位工资标准")
    db.commit()
    return {"message": "工资标准已保存", "id": standard.id}

@app.put("/api/salary-standards/{standard_id}")
def update_salary_standard(standard_id: int, data: SalaryStandardCreate, db: Session = Depends(get_db)):
    standard = db.query(SalaryStandard).filter(SalaryStandard.id == standard_id).first()
    if not standard:
        raise HTTPException(status_code=404, detail="工资标准不存在")
    standard.store_id = data.store_id
    standard.position = data.position
    standard.base_salary = data.base_salary
    standard.full_attendance_bonus = data.full_attendance_bonus
    standard.allowance = data.allowance
    standard.public_leave_days = data.public_leave_days
    standard.standard_work_days = data.standard_work_days
    standard.min_net_salary = data.min_net_salary
    standard.max_net_salary = data.max_net_salary
    # 满勤判断标准
    standard.allow_late_minutes = data.allow_late_minutes
    standard.allow_early_leave_minutes = data.allow_early_leave_minutes
    standard.allow_sick_leave_days = data.allow_sick_leave_days
    standard.allow_personal_leave_days = data.allow_personal_leave_days
    standard.allow_personal_leave_2h_count = data.allow_personal_leave_2h_count
    standard.allow_missing_count = data.allow_missing_count
    standard.allow_absent_days = data.allow_absent_days
    standard.description = data.description
    standard.is_active = True
    log_operation(db, "系统", "修改", "工资标准", standard.id, standard.position, "修改店面岗位工资标准")
    db.commit()
    return {"message": "工资标准已修改", "id": standard.id}

@app.delete("/api/salary-standards/{standard_id}")
def delete_salary_standard(standard_id: int, db: Session = Depends(get_db)):
    standard = db.query(SalaryStandard).filter(SalaryStandard.id == standard_id).first()
    if not standard:
        raise HTTPException(status_code=404, detail="工资标准不存在")
    standard.is_active = False
    log_operation(db, "系统", "删除", "工资标准", standard.id, standard.position, "停用店面岗位工资标准")
    db.commit()
    return {"message": "工资标准已删除"}

@app.post("/api/salary-standards/sync-from-attendance-rules")
def sync_salary_standards_from_rules(store_id: int = None, db: Session = Depends(get_db)):
    query = db.query(PositionAttendanceRule).filter(PositionAttendanceRule.is_active == True)
    if store_id:
        query = query.filter(PositionAttendanceRule.store_id == store_id)
    rules = query.all()
    synced = 0
    for rule in rules:
        standards = db.query(SalaryStandard).filter(
            SalaryStandard.store_id == rule.store_id,
            SalaryStandard.position == rule.position,
            SalaryStandard.is_active == True
        ).order_by(SalaryStandard.id).all()
        if standards:
            standard = standards[0]
            for duplicate in standards[1:]:
                duplicate.is_active = False
                duplicate.description = "重复岗位标准，已由考勤规则同步时停用"
        else:
            standard = SalaryStandard(store_id=rule.store_id, position=rule.position)
            db.add(standard)
        standard.base_salary = rule.base_salary or 0
        standard.full_attendance_bonus = rule.full_attendance_bonus or 0
        standard.allowance = rule.allowance or 0
        standard.public_leave_days = rule.public_leave_days or 0
        standard.standard_work_days = rule.work_days_per_month or 0
        standard.description = "由考勤规则同步"
        synced += 1
    log_operation(db, "系统", "同步", "工资标准", None, None, f"从考勤规则同步{synced}条工资标准")
    db.commit()
    return {"message": f"已同步{synced}条工资标准", "synced": synced}

@app.post("/api/salary-standards/sync-from-employees")
def sync_salary_standards_from_employee_salary_info(store_id: int = None, db: Session = Depends(get_db)):
    synced, with_differences = sync_salary_standards_from_employees(db, store_id)
    log_operation(db, "系统", "同步", "工资标准", None, None, f"从员工工资信息生成{synced}条工资标准，其中{with_differences}条同岗工资存在差异")
    db.commit()
    return {
        "message": f"已从员工工资信息生成{synced}条工资标准",
        "synced": synced,
        "with_differences": with_differences
    }

@app.get("/api/positions")
def get_positions(store_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Employee.position).distinct()
    if store_id:
        query = query.filter(Employee.store_id == store_id)
    positions = [p[0] for p in query.all() if p[0]]
    positions.sort()
    return positions

@app.get("/api/employees", response_model=List[dict])
def get_employees(store_id: int = None, position: str = None, status: str = None, name: str = None, db: Session = Depends(get_db)):
    query = db.query(Employee)
    if store_id:
        query = query.filter(Employee.store_id == store_id)
    if position:
        query = query.filter(Employee.position == position)
    if status:
        query = query.filter(Employee.status == status)
    elif not name:
        query = query.filter(Employee.is_active == True)
    if name:
        query = query.filter(Employee.name.like(f"%{name}%"))
    employees = query.all()
    return [{"id": e.id, "employee_id": e.employee_id, "name": e.name, "id_card": e.id_card,
             "position": e.position, "store_id": e.store_id, "store_name": e.store.name if e.store else "-",
             "base_salary": e.base_salary or 0, "hourly_rate": e.hourly_rate or 0,
             "phone": e.phone or "",
             "hire_date": e.hire_date.isoformat() if e.hire_date else None,
             "status": e.status or "在职", "probation": e.probation or False,
             "work_years": e.work_years or 0, "seniority_bonus": e.seniority_bonus or 0,
             "full_attendance_bonus": e.full_attendance_bonus or 0,
             "allowance": e.allowance or 0, "public_leave_days": e.public_leave_days or 0,
             "is_active": e.is_active} for e in employees]

class EmployeeCreate(BaseModel):
    store_id: int
    employee_id: str = ""
    name: str
    id_card: str = ""
    position: str = ""
    shift: str = "常日班"
    base_salary: float = 0.0
    hourly_rate: float = 0.0
    full_attendance_bonus: float = 0.0
    allowance: float = 0.0
    public_leave_days: float = 0.0
    phone: str = ""
    hire_date: str = ""
    probation: bool = True
    status: str = "在职"

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('员工姓名不能为空')
        return v.strip()

class EmployeeUpdate(BaseModel):
    name: str = ""
    id_card: str = ""
    position: str = ""
    phone: str = ""
    hire_date: str = None
    probation: bool = False
    status: str = "在职"
    work_years: float = 0
    seniority_bonus: float = 0
    base_salary: float = 0
    full_attendance_bonus: float = 0
    allowance: float = 0
    public_leave_days: float = 0

@app.post("/api/employees")
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    if not data.employee_id or not data.employee_id.strip():
        max_emp = db.query(Employee).filter(Employee.store_id == data.store_id).order_by(Employee.id.desc()).first()
        if max_emp and max_emp.employee_id:
            import re
            match = re.search(r'(\d+)$', max_emp.employee_id)
            if match:
                next_num = int(match.group(1)) + 1
                data.employee_id = f"EMP{data.store_id}{next_num:04d}"
            else:
                data.employee_id = f"EMP{data.store_id}0001"
        else:
            data.employee_id = f"EMP{data.store_id}0001"

    existing = db.query(Employee).filter(Employee.employee_id == data.employee_id, Employee.store_id == data.store_id).first()
    id_card = clean_optional_text(data.id_card)
    if existing:
        existing.name = data.name
        existing.id_card = id_card
        existing.position = data.position
        existing.shift = data.shift
        existing.base_salary = data.base_salary
        existing.hourly_rate = data.hourly_rate
        existing.full_attendance_bonus = data.full_attendance_bonus
        existing.allowance = data.allowance
        existing.public_leave_days = data.public_leave_days
        existing.phone = data.phone
        existing.probation = data.probation
        existing.status = data.status
        if data.hire_date:
            try:
                from datetime import datetime
                existing.hire_date = datetime.strptime(data.hire_date, "%Y-%m-%d").date()
            except:
                pass
        db.commit()
        return {"message": "员工已更新", "id": existing.id}
    employee = Employee(
        store_id=data.store_id,
        employee_id=data.employee_id,
        name=data.name,
        id_card=id_card,
        position=data.position,
        shift=data.shift,
        base_salary=data.base_salary,
        hourly_rate=data.hourly_rate,
        full_attendance_bonus=data.full_attendance_bonus,
        allowance=data.allowance,
        public_leave_days=data.public_leave_days,
        phone=data.phone,
        probation=data.probation,
        status=data.status
    )
    if data.hire_date:
        try:
            from datetime import datetime
            employee.hire_date = datetime.strptime(data.hire_date, "%Y-%m-%d").date()
        except:
            pass
    db.add(employee)
    db.commit()
    return {"message": "员工创建成功", "id": employee.id}

@app.put("/api/employees/{employee_id}")
def update_employee(employee_id: int, data: EmployeeUpdate, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    
    if data.name and data.name != employee.name:
        if employee.former_names:
            former_names_list = [n.strip() for n in employee.former_names.split(',') if n.strip()]
        else:
            former_names_list = []
        if employee.name not in former_names_list:
            former_names_list.append(employee.name)
            employee.former_names = ','.join(former_names_list)
    
    employee.name = data.name
    employee.id_card = clean_optional_text(data.id_card)
    employee.position = data.position
    employee.phone = data.phone
    if data.hire_date:
        from datetime import datetime
        employee.hire_date = datetime.strptime(data.hire_date, "%Y-%m-%d").date()
    employee.probation = data.probation
    employee.status = data.status
    if data.status == "离职":
        employee.is_active = False
    else:
        employee.is_active = True
    employee.work_years = data.work_years
    employee.seniority_bonus = data.seniority_bonus
    employee.base_salary = data.base_salary
    employee.full_attendance_bonus = data.full_attendance_bonus
    employee.allowance = data.allowance
    employee.public_leave_days = data.public_leave_days
    db.commit()
    return {"message": "员工已修改", "id": employee_id}

@app.delete("/api/employees/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    employee.is_active = False
    db.commit()
    return {"message": "员工已删除", "id": employee_id}

@app.get("/api/employees/export-template")
def export_salary_template(store_id: int = None, db: Session = Depends(get_db)):
    import pandas as pd
    from fastapi.responses import StreamingResponse
    import io

    query = db.query(Employee).filter(Employee.is_active == True)
    if store_id:
        query = query.filter(Employee.store_id == store_id)
    employees = query.order_by(Employee.name).all()
    
    data = []
    for e in employees:
        data.append({
            '员工ID': e.id,
            '姓名': e.name,
            '入职时间': e.hire_date.strftime('%Y-%m-%d') if e.hire_date else '',
            '基本工资': e.base_salary or 0,
            '满勤奖': e.full_attendance_bonus or 0,
            '工龄工资': e.seniority_bonus or 0,
            '补助': e.allowance or 0,
            '公休天数': e.public_leave_days or 0,
            '每月应出勤天数': 0
        })
    
    df = pd.DataFrame(data)

    output = io.BytesIO()
    df.to_excel(output, index=False, sheet_name='工资信息')
    output.seek(0)

    from fastapi.responses import Response
    headers = {'Content-Disposition': 'attachment; filename*=UTF-8\'\'%E5%91%98%E5%B7%A5%E5%B7%A5%E8%B5%84%E4%BF%A1%E6%81%AF%E6%A8%A1%E6%9D%BF.xlsx'}
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=headers
    )

@app.post("/api/employees/import-from-excel")
def import_employees_from_excel(store_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    import pandas as pd
    import io

    try:
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取Excel失败: {str(e)}")

    imported_count = 0
    skipped_count = 0
    skipped_details = []

    required_cols = ['姓名', '职务']
    for col in required_cols:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"缺少必要列: {col}")

    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店面不存在")

    last_num = 0
    all_emp_ids = db.query(Employee.employee_id).all()
    import re
    existing_nums = set()
    for (emp_id,) in all_emp_ids:
        if emp_id:
            match = re.search(r'(\d+)$', emp_id)
            if match:
                num = int(match.group(1))
                existing_nums.add(num)
                if num > last_num:
                    last_num = num

    def get_next_emp_id():
        nonlocal last_num
        while last_num + 1 in existing_nums:
            last_num += 1
        last_num += 1
        return f"AUTO{last_num}"

    for idx, row in df.iterrows():
        try:
            name = str(row.get('姓名', '')).strip()
            position = str(row.get('职务', '')).strip() if pd.notna(row.get('职务')) else ''

            if not name:
                skipped_count += 1
                skipped_details.append(f"行{idx+2}: 姓名为空")
                continue

            existing = db.query(Employee).filter(Employee.name == name, Employee.store_id == store_id).first()
            if existing:
                if position:
                    existing.position = position
                if pd.notna(row.get('电话')):
                    existing.phone = str(row.get('电话', ''))
                imported_count += 1
            else:
                new_emp = Employee(
                    store_id=store_id,
                    employee_id=get_next_emp_id(),
                    name=name,
                    position=position or '未知',
                    phone=str(row.get('电话', '')) if pd.notna(row.get('电话')) else '',
                    is_active=True
                )
                db.add(new_emp)
                imported_count += 1
        except Exception as e:
            skipped_count += 1
            skipped_details.append(f"行{idx+2}: {str(e)}")
            continue

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库保存失败: {str(e)}")

    skip_msg = ""
    if skipped_details:
        skip_msg = "跳过" + str(skipped_count) + "条: " + "; ".join(skipped_details[:10])
        if len(skipped_details) > 10:
            skip_msg += f"...等共{skipped_count}条"

    return {"imported": imported_count, "skipped": skipped_count, "skip_details": skip_msg}

@app.post("/api/employees/import-salary-info")
def import_salary_info(file: UploadFile = File(...), store_id: int = None, db: Session = Depends(get_db)):
    import pandas as pd
    import io

    try:
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取Excel失败: {str(e)}")

    imported_count = 0
    skipped_details = []

    column_mapping = {
        '姓名': 'name',
        '姓 名': 'name',
        '姓名 ': 'name',
        '岗位': 'position',
        '职务': 'position',
        '职称': 'position',
        '入职时间': 'hire_date',
        '入职日期': 'hire_date',
        '基本工资': 'base_salary',
        '工资标准': 'base_salary',
        '底薪': 'base_salary',
        '满勤奖': 'full_attendance_bonus',
        '满勤': 'full_attendance_bonus',
        '全勤奖': 'full_attendance_bonus',
        '全勤': 'full_attendance_bonus',
        '工龄工资': 'seniority_bonus',
        '工龄': 'seniority_bonus',
        '补助': 'allowance',
        '奖励补助': 'allowance',
        '奖励': 'bonus',
        '公休天数': 'public_leave_days',
        '月公休数': 'public_leave_days',
        '公休': 'public_leave_days',
        '应公休': 'public_leave_days',
        '每月应出勤天数': 'work_days_per_month',
        '月天数': 'work_days_per_month',
    }

    df.columns = [column_mapping.get(normalize_header_text(col), column_mapping.get(str(col).strip(), str(col).strip())) for col in df.columns]

    for idx, row in df.iterrows():
        try:
            emp_id = row.get('id') or row.get('员工ID')
            name = str(row['name']).strip() if 'name' in row and pd.notna(row['name']) else ''

            if emp_id:
                try:
                    employee = db.query(Employee).filter(Employee.id == int(emp_id)).first()
                except:
                    employee = None
            elif name:
                query = db.query(Employee).filter(Employee.name == name)
                if store_id:
                    query = query.filter(Employee.store_id == store_id)
                employee = query.first()
            else:
                skipped_details.append(f"行{idx+2}: 员工ID和姓名都为空")
                continue

            if not employee:
                skipped_details.append(f"行{idx+2}: 员工不存在或未选中店面")
                continue

            if name:
                employee.name = name
            if 'position' in row and pd.notna(row['position']) and str(row['position']).strip():
                employee.position = str(row['position']).strip()

            if 'hire_date' in row and pd.notna(row['hire_date']):
                try:
                    hire_date_val = row['hire_date']
                    parsed_date = None
                    if isinstance(hire_date_val, str):
                        for fmt in ["%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y.%d.%m"]:
                            try:
                                parsed_date = datetime.strptime(hire_date_val, fmt).date()
                                break
                            except:
                                continue
                    elif isinstance(hire_date_val, datetime):
                        parsed_date = hire_date_val.date()
                    elif isinstance(hire_date_val, pd.Timestamp):
                        parsed_date = hire_date_val.date()
                    if parsed_date:
                        employee.hire_date = parsed_date
                except:
                    pass

            if 'base_salary' in row and pd.notna(row['base_salary']):
                try:
                    employee.base_salary = parse_money(row['base_salary'])
                except:
                    pass

            if 'full_attendance_bonus' in row and pd.notna(row['full_attendance_bonus']):
                try:
                    employee.full_attendance_bonus = parse_money(row['full_attendance_bonus'])
                except:
                    pass

            if 'seniority_bonus' in row and pd.notna(row['seniority_bonus']):
                try:
                    employee.seniority_bonus = parse_money(row['seniority_bonus'])
                except:
                    pass

            if 'allowance' in row and pd.notna(row['allowance']):
                try:
                    employee.allowance = parse_money(row['allowance'])
                except:
                    pass
            if 'bonus' in row and pd.notna(row['bonus']):
                try:
                    if 'allowance' in row and pd.notna(row['allowance']):
                        employee.allowance = (employee.allowance or 0) + parse_money(row['bonus'])
                    else:
                        employee.allowance = parse_money(row['bonus'])
                except:
                    pass

            if 'public_leave_days' in row and pd.notna(row['public_leave_days']):
                try:
                    employee.public_leave_days = parse_money(row['public_leave_days'])
                except:
                    pass

            imported_count += 1
        except Exception as e:
            skipped_details.append(f"行{idx+2}: {str(e)}")
            continue

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库保存失败: {str(e)}")

    synced_standards, standard_differences = sync_salary_standards_from_employees(db, store_id)
    log_operation(db, "系统", "导入", "员工工资信息", None, None, f"导入{imported_count}条员工工资信息，并生成{synced_standards}条岗位工资标准")
    db.commit()

    skip_msg = f"跳过{len(skipped_details)}条: " + "; ".join(skipped_details[:10]) if skipped_details else ""
    if len(skipped_details) > 10:
        skip_msg += f"...等共{len(skipped_details)}条"
    return {
        "message": "工资信息导入完成",
        "imported": imported_count,
        "skipped": len(skipped_details),
        "skip_details": skip_msg,
        "standards_synced": synced_standards,
        "standard_differences": standard_differences
    }

@app.post("/api/salary-audit/import")
def import_salary_draft(
    year: int,
    month: int,
    store_id: int = None,
    uploaded_by: str = "系统",
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    import pandas as pd
    import io

    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="月份必须在1-12之间")
    if store_id:
        store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
        if not store:
            raise HTTPException(status_code=404, detail="店面不存在")

    try:
        contents = file.file.read()
        df = load_salary_draft_dataframe(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取Excel失败: {str(e)}")

    column_mapping = {
        '员工ID': 'employee_id',
        '员工编号': 'employee_id',
        '工号': 'employee_id',
        '姓名': 'name',
        '员工姓名': 'name',
        '姓名': 'name',
        '姓名_2': 'name',
        '姓名_3': 'name',
        '姓名称': 'name',
        '姓 名': 'name',
        '姓名 ': 'name',
        '姓   名': 'name',
        '身份证': 'id_card',
        '身份证号': 'id_card',
        '店面': 'store_name',
        '门店': 'store_name',
        '职务': 'position',
        '职称': 'position',
        '岗位': 'position',
        '工资标准': 'salary_standard',
        '基本工资': 'base_salary',
        '底薪': 'base_salary',
        '提成': 'commission',
        '奖金': 'bonus',
        '补助': 'allowance',
        '津贴': 'allowance',
        '奖励补助_补助': 'allowance',
        '满勤奖': 'full_attendance_bonus',
        '满勤': 'full_attendance_bonus',
        '全勤奖': 'full_attendance_bonus',
        '扣款': 'deduction',
        '应扣款': 'deduction',
        '实发工资': 'net_salary',
        '实际发放': 'actual_paid',
        '实发': 'net_salary',
        '备注': 'remark',
    }
    df.columns = [column_mapping.get(normalize_header_text(col), column_mapping.get(str(col).strip(), str(col).strip())) for col in df.columns]
    if 'name' not in df.columns:
        raise HTTPException(status_code=400, detail='工资表缺少必要列：姓名')

    batch = SalaryImportBatch(
        year=year,
        month=month,
        store_id=store_id,
        file_name=file.filename or "",
        uploaded_by=uploaded_by,
        row_count=0,
        total_net_salary=0,
        status="imported"
    )
    db.add(batch)
    db.flush()

    imported_count = 0
    skipped_details = []
    total_net_salary = 0.0

    for idx, row in df.iterrows():
        name = str(row.get('name', '')).strip() if pd.notna(row.get('name', '')) else ''
        if not name or name.lower() == 'nan':
            skipped_details.append(f"行{idx + 2}: 姓名为空")
            continue

        raw_employee_id = str(row.get('employee_id', '')).strip() if 'employee_id' in row and pd.notna(row.get('employee_id')) else ''
        raw_id_card = str(row.get('id_card', '')).strip() if 'id_card' in row and pd.notna(row.get('id_card')) else ''
        query = db.query(Employee)
        if store_id:
            query = query.filter(Employee.store_id == store_id)
        employee = None
        if raw_employee_id:
            employee = query.filter(Employee.employee_id == raw_employee_id).first()
        if not employee and raw_id_card:
            employee = query.filter(Employee.id_card == raw_id_card).first()
        if not employee:
            employee = query.filter(Employee.name == name).first()

        base_salary = parse_money(row.get('salary_standard')) if 'salary_standard' in row else (parse_money(row.get('base_salary')) if 'base_salary' in row else 0)
        commission = parse_money(row.get('commission')) if 'commission' in row else 0
        bonus = parse_money(row.get('bonus')) if 'bonus' in row else 0
        allowance = parse_money(row.get('allowance')) if 'allowance' in row else 0
        full_attendance_bonus = parse_money(row.get('full_attendance_bonus')) if 'full_attendance_bonus' in row else 0
        deduction = parse_money(row.get('deduction')) if 'deduction' in row else 0
        if deduction == 0:
            deduction_cols = [col for col in df.columns if any(k in str(col) for k in ['扣款_', '病假', '事假', '旷工', '迟到', '未打卡', '罚款', '挂账', '差货款', '自费出库', '破损'])]
            deduction = sum(parse_money(row.get(col)) for col in deduction_cols)
        net_salary = parse_money(row.get('net_salary')) if 'net_salary' in row else (parse_money(row.get('actual_paid')) if 'actual_paid' in row else base_salary + commission + bonus + allowance + full_attendance_bonus - deduction)
        total_net_salary += net_salary

        raw_data = {}
        for col in df.columns:
            val = row.get(col)
            if pd.isna(val):
                raw_data[col] = ""
            elif isinstance(val, (datetime, date)):
                raw_data[col] = val.isoformat()
            else:
                raw_data[col] = str(val)

        draft = SalaryDraft(
            batch_id=batch.id,
            employee_id=employee.id if employee else None,
            raw_employee_id=raw_employee_id,
            raw_id_card=raw_id_card,
            employee_name=name,
            store_name=str(row.get('store_name', '')).strip() if 'store_name' in row and pd.notna(row.get('store_name')) else (employee.store.name if employee and employee.store else ''),
            position=str(row.get('position', '')).strip() if 'position' in row and pd.notna(row.get('position')) else (employee.position if employee else ''),
            base_salary=base_salary,
            commission=commission,
            bonus=bonus,
            allowance=allowance,
            full_attendance_bonus=full_attendance_bonus,
            deduction=deduction,
            net_salary=net_salary,
            remark=str(row.get('remark', '')).strip() if 'remark' in row and pd.notna(row.get('remark')) else '',
            raw_data=json.dumps(raw_data, ensure_ascii=False)
        )
        db.add(draft)
        imported_count += 1

    batch.row_count = imported_count
    batch.total_net_salary = total_net_salary
    db.commit()

    audit_count = run_salary_audit(db, batch.id)
    log_operation(db, uploaded_by, "导入", "工资底稿", batch.id, f"{year}-{month:02d}", f"导入{imported_count}条，生成审计异常{audit_count}条")
    return {
        "message": "工资底稿导入并审计完成",
        "batch_id": batch.id,
        "imported": imported_count,
        "skipped": len(skipped_details),
        "skip_details": "; ".join(skipped_details[:10]),
        "audit_count": audit_count
    }

@app.get("/api/salary-audit/batches")
def get_salary_audit_batches(year: int = None, month: int = None, store_id: int = None, db: Session = Depends(get_db)):
    query = db.query(SalaryImportBatch)
    if year:
        query = query.filter(SalaryImportBatch.year == year)
    if month:
        query = query.filter(SalaryImportBatch.month == month)
    if store_id:
        query = query.filter(SalaryImportBatch.store_id == store_id)
    batches = query.order_by(SalaryImportBatch.created_at.desc()).all()
    result = []
    for b in batches:
        pending = db.query(SalaryAuditResult).filter(SalaryAuditResult.batch_id == b.id, SalaryAuditResult.status == "pending").count()
        total = db.query(SalaryAuditResult).filter(SalaryAuditResult.batch_id == b.id).count()
        result.append({
            "id": b.id,
            "year": b.year,
            "month": b.month,
            "store_id": b.store_id,
            "store_name": b.store.name if b.store else "全部店面",
            "file_name": b.file_name,
            "uploaded_by": b.uploaded_by,
            "row_count": b.row_count,
            "total_net_salary": b.total_net_salary,
            "audit_total": total,
            "audit_pending": pending,
            "status": b.status,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else ""
        })
    return result

@app.post("/api/salary-audit/{batch_id}/rerun")
def rerun_salary_audit(batch_id: int, operator: str = "系统", db: Session = Depends(get_db)):
    count = run_salary_audit(db, batch_id)
    log_operation(db, operator, "重跑审计", "工资底稿", batch_id, str(batch_id), f"重新生成审计异常{count}条")
    return {"message": "审计已重跑", "audit_count": count}

@app.get("/api/salary-audit/{batch_id}/drafts")
def get_salary_drafts(batch_id: int, db: Session = Depends(get_db)):
    drafts = db.query(SalaryDraft).filter(SalaryDraft.batch_id == batch_id).order_by(SalaryDraft.employee_name).all()
    return [{
        "id": d.id,
        "employee_id": d.employee.employee_id if d.employee else d.raw_employee_id,
        "employee_name": d.employee_name,
        "matched": bool(d.employee_id),
        "store_name": d.store_name,
        "position": d.position,
        "base_salary": d.base_salary,
        "commission": d.commission,
        "bonus": d.bonus,
        "allowance": d.allowance,
        "full_attendance_bonus": d.full_attendance_bonus,
        "deduction": d.deduction,
        "net_salary": d.net_salary,
        "remark": d.remark
    } for d in drafts]

@app.get("/api/salary-audit/{batch_id}/results")
def get_salary_audit_results(
    batch_id: int,
    status: str = None,
    severity: str = None,
    rule_code: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(SalaryAuditResult).filter(SalaryAuditResult.batch_id == batch_id)
    if status:
        query = query.filter(SalaryAuditResult.status == status)
    if severity:
        query = query.filter(SalaryAuditResult.severity == severity)
    if rule_code:
        query = query.filter(SalaryAuditResult.rule_code == rule_code)
    audits = query.order_by(SalaryAuditResult.severity, SalaryAuditResult.id).all()
    summary = {"total": 0, "pending": 0, "confirmed": 0, "returned": 0, "ignored": 0, "critical": 0, "warning": 0, "info": 0}
    all_audits = db.query(SalaryAuditResult).filter(SalaryAuditResult.batch_id == batch_id).all()
    for a in all_audits:
        summary["total"] += 1
        summary[a.status] = summary.get(a.status, 0) + 1
        summary[a.severity] = summary.get(a.severity, 0) + 1
    return {
        "summary": summary,
        "data": [{
            "id": a.id,
            "draft_id": a.draft_id,
            "employee_name": a.draft.employee_name if a.draft else (a.employee.name if a.employee else ""),
            "store_name": a.draft.store_name if a.draft else (a.employee.store.name if a.employee and a.employee.store else ""),
            "position": a.draft.position if a.draft else (a.employee.position if a.employee else ""),
            "net_salary": a.draft.net_salary if a.draft else 0,
            "deduction": a.draft.deduction if a.draft else 0,
            "rule_code": a.rule_code,
            "rule_name": a.rule_name,
            "severity": a.severity,
            "description": a.description,
            "status": a.status,
            "reviewer": a.reviewer or "",
            "review_note": a.review_note or "",
            "reviewed_at": a.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if a.reviewed_at else ""
        } for a in audits]
    }

@app.put("/api/salary-audit/results/{audit_id}")
def review_salary_audit_result(audit_id: int, data: SalaryAuditReviewRequest, db: Session = Depends(get_db)):
    audit = db.query(SalaryAuditResult).filter(SalaryAuditResult.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="审计结果不存在")
    before = audit.status
    audit.status = data.status
    audit.reviewer = data.reviewer or "系统"
    audit.review_note = data.review_note or ""
    audit.reviewed_at = datetime.now()
    log_operation(db, audit.reviewer, "审核", "工资审计", audit.id, audit.rule_name, f"{before} -> {audit.status}: {audit.review_note}")
    db.commit()
    return {"message": "审计结果已处理"}

@app.get("/api/salary-audit/{batch_id}/export")
def export_salary_audit_report(batch_id: int, db: Session = Depends(get_db)):
    import pandas as pd
    from fastapi.responses import StreamingResponse
    import io
    from urllib.parse import quote

    batch = db.query(SalaryImportBatch).filter(SalaryImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="工资批次不存在")
    audits = db.query(SalaryAuditResult).filter(SalaryAuditResult.batch_id == batch_id).order_by(SalaryAuditResult.id).all()
    data = []
    for a in audits:
        data.append({
            "月份": f"{batch.year}-{batch.month:02d}",
            "店面": a.draft.store_name if a.draft else (a.employee.store.name if a.employee and a.employee.store else ""),
            "姓名": a.draft.employee_name if a.draft else (a.employee.name if a.employee else ""),
            "岗位": a.draft.position if a.draft else (a.employee.position if a.employee else ""),
            "实发工资": a.draft.net_salary if a.draft else 0,
            "扣款": a.draft.deduction if a.draft else 0,
            "异常类型": a.rule_name,
            "严重等级": a.severity,
            "异常说明": a.description,
            "处理状态": a.status,
            "审核人": a.reviewer or "",
            "审核备注": a.review_note or "",
            "审核时间": a.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if a.reviewed_at else "",
        })
    output = io.BytesIO()
    pd.DataFrame(data).to_excel(output, index=False, sheet_name="工资审计报告")
    output.seek(0)
    filename = f"salary_audit_{batch.year}_{batch.month:02d}_batch{batch.id}.xlsx"
    headers = {'Content-Disposition': f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'}
    return StreamingResponse(output, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)

class PositionRuleCreate(BaseModel):
    store_id: int
    position: str
    start_time: str
    end_time: str
    is_overnight: bool = False
    is_rotating_shift: bool = False

@app.get("/api/attendance/rules", response_model=List[dict])
def get_attendance_rules(store_id: int = None, db: Session = Depends(get_db)):
    query = db.query(PositionAttendanceRule).filter(PositionAttendanceRule.is_active == True)
    if store_id:
        query = query.filter(PositionAttendanceRule.store_id == store_id)
    rules = query.all()
    return [{"id": r.id, "store_id": r.store_id, "store_name": r.store.name if r.store else "-",
             "position": r.position, "shift": r.shift or "常日班",
             "start_time": r.start_time, "end_time": r.end_time,
             "is_overnight": r.is_overnight, "is_rotating_shift": r.is_rotating_shift,
             "is_active": r.is_active, "base_salary": r.base_salary or 0,
             "full_attendance_bonus": r.full_attendance_bonus or 0,
             "allowance": r.allowance or 0, "public_leave_days": r.public_leave_days or 0} for r in rules]

@app.post("/api/attendance/rules")
def create_attendance_rule(data: PositionRuleCreate, db: Session = Depends(get_db)):
    rule = PositionAttendanceRule(
        store_id=data.store_id,
        position=data.position,
        start_time=data.start_time,
        end_time=data.end_time,
        is_overnight=data.is_overnight,
        is_rotating_shift=data.is_rotating_shift
    )
    db.add(rule)
    db.commit()
    return {"message": "考勤规则创建成功", "id": rule.id}

@app.put("/api/attendance/rules/{rule_id}")
def update_attendance_rule(rule_id: int, data: PositionRuleCreate, db: Session = Depends(get_db)):
    rule = db.query(PositionAttendanceRule).filter(PositionAttendanceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule.position = data.position
    rule.start_time = data.start_time
    rule.end_time = data.end_time
    rule.is_overnight = data.is_overnight
    rule.is_rotating_shift = data.is_rotating_shift
    db.commit()
    return {"message": "考勤规则已修改", "id": rule_id}

class PositionRuleSalaryUpdate(BaseModel):
    start_time: str = None
    end_time: str = None
    is_overnight: bool = None
    base_salary: float = None
    full_attendance_bonus: float = None
    allowance: float = None
    public_leave_days: float = None
    is_rotating_shift: bool = None

@app.patch("/api/attendance/rules/{rule_id}")
def patch_attendance_rule(rule_id: int, data: PositionRuleSalaryUpdate, db: Session = Depends(get_db)):
    rule = db.query(PositionAttendanceRule).filter(PositionAttendanceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    if data.start_time is not None:
        rule.start_time = data.start_time
    if data.end_time is not None:
        rule.end_time = data.end_time
    if data.is_overnight is not None:
        rule.is_overnight = data.is_overnight
    if data.base_salary is not None:
        rule.base_salary = data.base_salary
    if data.full_attendance_bonus is not None:
        rule.full_attendance_bonus = data.full_attendance_bonus
    if data.allowance is not None:
        rule.allowance = data.allowance
    if data.public_leave_days is not None:
        rule.public_leave_days = data.public_leave_days
    if data.is_rotating_shift is not None:
        rule.is_rotating_shift = data.is_rotating_shift
    db.commit()
    return {"message": "考勤规则已修改", "id": rule_id}

@app.delete("/api/attendance/rules/{rule_id}")
def delete_attendance_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(PositionAttendanceRule).filter(PositionAttendanceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule.is_active = False
    db.commit()
    return {"message": "考勤规则已删除", "id": rule_id}

@app.delete("/api/attendance/rules/store/{store_id}")
def delete_store_rules(store_id: int, db: Session = Depends(get_db)):
    rules = db.query(PositionAttendanceRule).filter(PositionAttendanceRule.store_id == store_id).all()
    count = len(rules)
    for rule in rules:
        rule.is_active = False
    db.commit()
    return {"message": f"已删除店面{store_id}的{count}条规则", "deleted": count}

class RuleCreate(BaseModel):
    store_id: int
    position: str
    start_time: str
    end_time: str
    is_overnight: bool = False
    is_rotating_shift: bool = False

@app.post("/api/attendance/rules")
def create_rule(data: RuleCreate, db: Session = Depends(get_db)):
    existing = db.query(PositionAttendanceRule).filter(
        PositionAttendanceRule.store_id == data.store_id,
        PositionAttendanceRule.position == data.position,
        PositionAttendanceRule.start_time == data.start_time,
        PositionAttendanceRule.is_active == True
    ).first()
    if existing:
        existing.end_time = data.end_time
        existing.is_overnight = data.is_overnight
        existing.is_rotating_shift = data.is_rotating_shift
        db.commit()
        return {"message": "规则已更新", "id": existing.id}
    rule = PositionAttendanceRule(
        store_id=data.store_id,
        position=data.position,
        start_time=data.start_time,
        end_time=data.end_time,
        is_overnight=data.is_overnight,
        is_rotating_shift=data.is_rotating_shift
    )
    db.add(rule)
    db.commit()
    return {"message": "规则已创建", "id": rule.id}

@app.post("/api/attendance/import-rules-excel")
def import_rules_from_excel(store_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    import pandas as pd
    import io
    
    try:
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取Excel失败: {str(e)}")
    
    imported_count = 0
    skipped_count = 0
    skipped_details = []
    
    column_mapping = {
        '岗位名称': '岗位',
        '岗位': '岗位',
        '职务': '岗位',
        '班次名称': '班次',
        '上班': '上班时间',
        '上班时间': '上班时间',
        '下班': '下班时间',
        '下班时间': '下班时间',
        '跨天': '是否跨天',
        '是否跨天': '是否跨天',
        '轮班': '是否轮班',
        '是否轮班': '是否轮班',
    }
    
    df.columns = [column_mapping.get(normalize_header_text(col), normalize_header_text(col)) for col in df.columns]
    df = df.loc[:, [c for c in df.columns if c and not str(c).startswith("未命名") and not str(c).startswith("Unnamed")]]

    required_columns = ["岗位", "班次", "上班时间", "下班时间"]
    allowed_columns = set(required_columns + ["是否跨天", "是否轮班"])
    missing_columns = [c for c in required_columns if c not in df.columns]
    extra_columns = [c for c in df.columns if c not in allowed_columns]
    if missing_columns:
        raise HTTPException(status_code=400, detail=f"考勤规则表缺少固定字段: {', '.join(missing_columns)}。请使用字段: 岗位、班次、上班时间、下班时间、是否跨天、是否轮班")
    if extra_columns:
        raise HTTPException(status_code=400, detail=f"考勤规则表包含不支持的字段: {', '.join(extra_columns)}。请只保留: 岗位、班次、上班时间、下班时间、是否跨天、是否轮班")
    
    shift_type_col = '班次' if '班次' in df.columns else None
    
    for idx, row in df.iterrows():
        try:
            position = str(row['岗位']).strip() if '岗位' in row and pd.notna(row['岗位']) else ''
            shift_name = str(row['班次']).strip() if '班次' in row and pd.notna(row['班次']) else ''
            raw_end_time = str(row['下班时间']).strip() if '下班时间' in row and pd.notna(row['下班时间']) else ''
            start_time = normalize_rule_time_value(row['上班时间'])
            end_time = normalize_rule_time_value(row['下班时间'])
            
            if not position or position == 'nan' or not shift_name or shift_name == 'nan' or not start_time or not end_time:
                skipped_count += 1
                skipped_details.append(f"行{idx + 2}: 岗位、班次、上班时间、下班时间不能为空")
                continue
            
            if not validate_hhmm(start_time):
                skipped_count += 1
                skipped_details.append(f"行{idx + 2}: 上班时间必须是HH:MM格式")
                continue
            
            if not validate_hhmm(end_time):
                skipped_count += 1
                skipped_details.append(f"行{idx + 2}: 下班时间必须是HH:MM格式")
                continue
            
            is_overnight = False
            is_rotating_shift = False
            
            if shift_type_col and pd.notna(row[shift_type_col]):
                shift_type = str(row[shift_type_col]).strip()
                if '夜班' in shift_type or '大夜班' in shift_type:
                    is_overnight = True
                elif '休息' in shift_type or '公休' in shift_type:
                    is_rotating_shift = True

            if '是否跨天' in row and pd.notna(row['是否跨天']):
                flag = str(row['是否跨天']).strip().lower()
                if flag in ["是", "1", "true", "yes", "y"]:
                    is_overnight = True
            if '是否轮班' in row and pd.notna(row['是否轮班']):
                flag = str(row['是否轮班']).strip().lower()
                if flag in ["是", "1", "true", "yes", "y"]:
                    is_rotating_shift = True
            
            if '次日' in raw_end_time:
                is_overnight = True

            try:
                start_h = int(start_time.split(':')[0])
                end_h = int(end_time.split(':')[0])
                if 0 <= end_h <= 12 and start_h >= 18:
                    is_overnight = True
                if end_h == 0:
                    is_overnight = True
            except:
                pass
            
        except Exception as e:
            skipped_count += 1
            skipped_details.append(f"行{idx + 2}: {str(e)}")
            continue
        
        existing = db.query(PositionAttendanceRule).filter(
            PositionAttendanceRule.store_id == store_id,
            PositionAttendanceRule.position == position,
            PositionAttendanceRule.start_time == start_time,
            PositionAttendanceRule.is_active == True
        ).first()
        
        if existing:
            existing.end_time = end_time
            existing.is_overnight = is_overnight
            existing.is_rotating_shift = is_rotating_shift
        else:
            rule = PositionAttendanceRule(
                store_id=store_id,
                position=position,
                start_time=start_time,
                end_time=end_time,
                is_overnight=is_overnight,
                is_rotating_shift=is_rotating_shift
            )
            db.add(rule)
        imported_count += 1
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库保存失败: {str(e)}")
    
    return {
        "message": "规则导入完成",
        "imported": imported_count,
        "skipped": skipped_count,
        "skip_details": "；".join(skipped_details[:20])
    }

@app.post("/api/attendance/import-checkin-excel")
def import_checkin_from_excel(store_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    import pandas as pd
    import io
    import re

    try:
        contents = file.file.read()
        
        xl = pd.ExcelFile(io.BytesIO(contents))
        sheet_names = xl.sheet_names
        
        df = None
        found = False
        
        for sheet_name in sheet_names:
            try:
                temp_df = pd.read_excel(io.BytesIO(contents), sheet_name=sheet_name, header=None)
                if len(temp_df) >= 5:
                    for check_row in range(min(10, len(temp_df))):
                        row_values = temp_df.iloc[check_row].astype(str).tolist()
                        if '最早' in row_values and '最晚' in row_values:
                            df = pd.read_excel(io.BytesIO(contents), sheet_name=sheet_name, header=None, skiprows=check_row+1)
                            found = True
                            break
                    if found:
                        break
            except:
                continue
        
        if not found or df is None:
            raise Exception("无法找到包含'最早'和'最晚'列的sheet")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取Excel失败: {str(e)}")
    
    imported_count = 0
    skipped_count = 0
    skip_details = []
    new_employee_count = 0

    employee_date_records = {}
    
    employees = db.query(Employee).filter(Employee.store_id == store_id).all()
    employee_name_map = {}
    for e in employees:
        clean_name = e.name.replace('（已离职）', '').replace('(已离职)', '').strip()
        employee_name_map[clean_name.lower()] = e
        if e.former_names:
            former_names = [n.strip() for n in e.former_names.split(',') if n.strip()]
            for fn in former_names:
                employee_name_map[fn.lower()] = e
    
    new_employees_map = {}
    
    for _, row in df.iterrows():
        try:
            date_str = str(row.iloc[0])
            name = str(row.iloc[1]).strip()
        except:
            skipped_count += 1
            skip_details.append(f"行{_+1}: 无法读取日期或姓名")
            continue
        
        if '时间' in date_str or '姓名' in name or name == 'nan':
            continue

        name = name.replace('（已离职）', '').replace('(已离职)', '').strip()

        position = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) and str(row.iloc[4]).strip() != 'nan' else '未分配'

        emp = None
        name_lower = name.lower()
        
        if name_lower in employee_name_map:
            emp = employee_name_map[name_lower]
        elif name_lower in new_employees_map:
            emp = new_employees_map[name_lower]
        
        if not emp:
            try:
                import random
                timestamp = int(datetime.now().timestamp())
                random_suffix = random.randint(1000, 9999)
                new_emp_id = f"AUTO{timestamp}{random_suffix}"
                
                emp = Employee(
                    employee_id=new_emp_id,
                    name=name,
                    store_id=store_id,
                    position=position,
                    is_active=True
                )
                db.add(emp)
                db.flush()
                new_employees_map[name_lower] = emp
                employee_name_map[name_lower] = emp
                new_employee_count += 1
            except Exception as e:
                import traceback
                print(f"创建员工失败: {name}, 错误: {str(e)}")
                print(traceback.format_exc())
                db.rollback()
                emp = None
        
        if not emp:
            skipped_count += 1
            skip_details.append(f"行{_+1}: 无法找到或创建员工 {name}")
            continue
        
        try:
            date_part = date_str.split(' ')[0]
            record_date = datetime.strptime(date_part, "%Y/%m/%d").date()
        except:
            skipped_count += 1
            skip_details.append(f"行{_+1}: 日期格式错误 {date_str}")
            continue
        
        key = (emp.id, record_date)
        if key not in employee_date_records:
            employee_date_records[key] = {'emp': emp, 'date': record_date, 'check_in_time': None, 'check_out_time': None, 'force_public_leave': False}
        
        earliest_str = str(row.iloc[8]).strip() if pd.notna(row.iloc[8]) else '未打卡'
        latest_str = str(row.iloc[9]).strip() if pd.notna(row.iloc[9]) else '未打卡'
        
        if earliest_str and earliest_str not in ['未打卡', 'nan', '--']:
            check_in_time = None
            if '次日' in earliest_str:
                actual_time_clean = earliest_str.replace('次日', '').strip()
                next_day = record_date + timedelta(days=1)
                try:
                    check_in_time = datetime.strptime(f"{next_day.strftime('%Y-%m-%d')} {actual_time_clean}", "%Y-%m-%d %H:%M:%S")
                except:
                    try:
                        check_in_time = datetime.strptime(f"{next_day.strftime('%Y-%m-%d')} {actual_time_clean}", "%Y-%m-%d %H:%M")
                    except:
                        pass
            else:
                try:
                    check_in_time = datetime.strptime(f"{record_date.strftime('%Y-%m-%d')} {earliest_str}", "%Y-%m-%d %H:%M:%S")
                except:
                    try:
                        check_in_time = datetime.strptime(f"{record_date.strftime('%Y-%m-%d')} {earliest_str}", "%Y-%m-%d %H:%M")
                    except:
                        pass
            
            if check_in_time:
                employee_date_records[key]['check_in_time'] = check_in_time
        
        if latest_str and latest_str not in ['未打卡', 'nan', '--']:
            if '次日' in latest_str:
                check_out_str_clean = latest_str.replace('次日', '').strip()
                next_day = record_date + timedelta(days=1)
                try:
                    employee_date_records[key]['check_out_time'] = datetime.strptime(f"{next_day.strftime('%Y-%m-%d')} {check_out_str_clean}", "%Y-%m-%d %H:%M:%S")
                except:
                    try:
                        employee_date_records[key]['check_out_time'] = datetime.strptime(f"{next_day.strftime('%Y-%m-%d')} {check_out_str_clean}", "%Y-%m-%d %H:%M")
                    except:
                        check_out_str_clean = re.sub(r'[^\d:]', '', check_out_str_clean)
                        try:
                            employee_date_records[key]['check_out_time'] = datetime.strptime(f"{next_day.strftime('%Y-%m-%d')} {check_out_str_clean}", "%Y-%m-%d %H:%M")
                        except:
                            pass
            else:
                try:
                    employee_date_records[key]['check_out_time'] = datetime.strptime(f"{record_date.strftime('%Y-%m-%d')} {latest_str}", "%Y-%m-%d %H:%M:%S")
                except:
                    try:
                        employee_date_records[key]['check_out_time'] = datetime.strptime(f"{record_date.strftime('%Y-%m-%d')} {latest_str}", "%Y-%m-%d %H:%M")
                    except:
                        pass
    
    repair_split_day_checkins(employee_date_records)

    rotating_shift_config = {}
    for key, rec in employee_date_records.items():
        emp_id = key[0]
        if emp_id not in rotating_shift_config:
            emp = rec['emp']
            pos_rules = db.query(PositionAttendanceRule).filter(
                PositionAttendanceRule.store_id == emp.store_id,
                PositionAttendanceRule.position == emp.position,
                PositionAttendanceRule.is_active == True,
                PositionAttendanceRule.is_rotating_shift == True
            ).all()
            if pos_rules:
                rotating_shift_config[emp_id] = {
                    'emp': emp,
                    'rules': pos_rules,
                    'shift_sequence': ['夜班', '白班', '休息']
                }

    for emp_id, config in rotating_shift_config.items():
        emp = config['emp']
        emp_records = []
        for k, r in employee_date_records.items():
            if k[0] == emp_id:
                emp_records.append({
                    'key': k,
                    'date': k[1],
                    'check_in_time': r['check_in_time'],
                    'check_out_time': r['check_out_time']
                })

        emp_records.sort(key=lambda x: x['date'])

        shift_idx = 0
        shift_sequence = config['shift_sequence']

        for rec_item in emp_records:
            check_in = rec_item['check_in_time']
            check_out = rec_item['check_out_time']

            expected_shift = shift_sequence[shift_idx % 3]

            if check_in and check_out:
                check_in_hour = check_in.hour
                check_out_hour = check_out.hour

                best_rule = None
                best_score = float('inf')
                for rule in config['rules']:
                    start_h = parse_time_to_hour(rule.start_time)
                    end_h = parse_time_to_hour(rule.end_time)
                    is_overnight = rule.is_overnight

                    if is_overnight:
                        if check_in_hour >= 20 or check_in_hour < 6:
                            expected_shift_this = '夜班'
                        else:
                            expected_shift_this = '白班'
                    else:
                        if 11 <= check_in_hour < 23:
                            expected_shift_this = '白班'
                        else:
                            expected_shift_this = '夜班'

                    if expected_shift_this == expected_shift:
                        score = abs(check_in_hour - start_h) + abs(check_out_hour - end_h) if check_out_hour != end_h else abs(check_in_hour - start_h)
                        if score < best_score:
                            best_score = score
                            best_rule = rule

                if expected_shift != '休息':
                    shift_idx += 1
            elif check_in and not check_out:
                if expected_shift == '休息':
                    employee_date_records[rec_item['key']]['check_out_time'] = None
                    employee_date_records[rec_item['key']]['check_in_time'] = None
                    shift_idx += 1
                else:
                    shift_idx += 1
            elif not check_in and check_out:
                prev_key = (emp_id, rec_item['date'] - timedelta(days=1))
                if prev_key in employee_date_records and employee_date_records[prev_key]['check_out_time'] is None:
                    employee_date_records[prev_key]['check_out_time'] = check_out
                    employee_date_records[rec_item['key']]['check_in_time'] = None
                else:
                    employee_date_records[rec_item['key']]['check_out_time'] = None
                shift_idx += 1
            else:
                if expected_shift != '休息':
                    shift_idx += 1
                shift_idx += 1

    rotating_ids = set(rotating_shift_config.keys())

    for key, rec in list(employee_date_records.items()):
        if key[0] in rotating_ids:
            continue
        check_out_time = rec['check_out_time']
        if check_out_time and check_out_time.hour >= 9:
            emp = rec['emp']
            check_out_date = check_out_time.date()
            record_date = rec['date']
            if check_out_date > record_date:
                next_key = (emp.id, check_out_date)
                if next_key in employee_date_records:
                    if employee_date_records[next_key]['check_in_time'] is None:
                        employee_date_records[next_key]['check_in_time'] = check_out_time
                        employee_date_records[key]['check_out_time'] = None
                else:
                    employee_date_records[next_key] = {'emp': emp, 'date': check_out_date, 'check_in_time': check_out_time, 'check_out_time': None, 'force_public_leave': False}
                    employee_date_records[key]['check_out_time'] = None

    for key, rec in list(employee_date_records.items()):
        if key[0] in rotating_ids:
            continue
        check_in_time = rec['check_in_time']
        if check_in_time and check_in_time.hour < 9:
            emp = rec['emp']
            check_in_date = check_in_time.date()
            record_date = rec['date']
            if check_in_date != record_date:
                prev_date = check_in_date - timedelta(days=1)
                prev_key = (emp.id, prev_date)
                if prev_key in employee_date_records:
                    if employee_date_records[prev_key]['check_out_time'] is None:
                        employee_date_records[prev_key]['check_out_time'] = check_in_time
                        employee_date_records[key]['check_in_time'] = None
                else:
                    employee_date_records[prev_key] = {'emp': emp, 'date': prev_date, 'check_in_time': None, 'check_out_time': check_in_time, 'force_public_leave': False}
                    employee_date_records[key]['check_in_time'] = None
            else:
                prev_date = check_in_date - timedelta(days=1)
                prev_key = (emp.id, prev_date)
                if prev_key in employee_date_records and employee_date_records[prev_key]['check_out_time'] is None:
                    employee_date_records[prev_key]['check_out_time'] = check_in_time
                    employee_date_records[key]['check_in_time'] = None

    for key, rec in employee_date_records.items():
        emp = rec['emp']
        record_date = rec['date']
        check_in_time = rec['check_in_time']
        check_out_time = rec['check_out_time']
        force_public_leave = rec.get('force_public_leave', False)

        is_rotating = False
        pos_rule = db.query(PositionAttendanceRule).filter(
            PositionAttendanceRule.store_id == emp.store_id,
            PositionAttendanceRule.position == emp.position,
            PositionAttendanceRule.is_active == True
        ).first()
        if pos_rule and pos_rule.is_rotating_shift:
            is_rotating = True

        existing = db.query(AttendanceResult).filter(
            AttendanceResult.employee_id == emp.id,
            AttendanceResult.date == record_date
        ).first()

        if existing:
            existing.check_in_time = check_in_time
            existing.check_out_time = check_out_time
            if force_public_leave:
                existing.result_morning = '公休'
                existing.result_afternoon = '公休'
            elif is_rotating and not check_in_time and not check_out_time:
                existing.result_morning = '公休'
                existing.result_afternoon = '公休'
            elif not check_in_time and not check_out_time:
                existing.result_morning = '上午缺卡'
                existing.result_afternoon = '下午缺卡'
            elif not check_in_time:
                existing.result_morning = '上午缺卡'
                existing.result_afternoon = '正常'
            elif not check_out_time:
                existing.result_morning = '正常'
                existing.result_afternoon = '下午缺卡'
            else:
                existing.result_morning = '正常'
                existing.result_afternoon = '正常'
            existing.updated_at = datetime.now()
            existing.status = 'pending'
        else:
            if force_public_leave:
                result_morning = '公休'
                result_afternoon = '公休'
            elif is_rotating and not check_in_time and not check_out_time:
                result_morning = '公休'
                result_afternoon = '公休'
            elif not check_in_time and not check_out_time:
                result_morning = '上午缺卡'
                result_afternoon = '下午缺卡'
            elif not check_in_time:
                result_morning = '上午缺卡'
                result_afternoon = '正常'
            elif not check_out_time:
                result_morning = '正常'
                result_afternoon = '下午缺卡'
            else:
                result_morning = '正常'
                result_afternoon = '正常'
            new_record = AttendanceResult(
                employee_id=emp.id,
                date=record_date,
                check_in_time=check_in_time,
                check_out_time=check_out_time,
                result_morning=result_morning,
                result_afternoon=result_afternoon,
                status='pending'
            )
            db.add(new_record)
            imported_count += 1
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库保存失败: {str(e)}")

    return {
        "message": f"导入完成",
        "imported": imported_count,
        "skipped": skipped_count,
        "new_employees": new_employee_count,
        "skip_details": "\n".join(skip_details) if skip_details else ""
    }

@app.post("/api/attendance/manual")
def add_manual_attendance(data: ManualAttendanceCreate, db: Session = Depends(get_db)):
    query = db.query(Employee).filter(Employee.is_active == True)
    if data.store_id:
        query = query.filter(Employee.store_id == data.store_id)
    emp = query.filter(Employee.name == data.name).first()
    if not emp:
        raise HTTPException(status_code=404, detail="员工不存在")

    record_date = datetime.strptime(data.date, "%Y-%m-%d").date()

    check_in_time = None
    if data.check_in:
        try:
            check_in_time = datetime.strptime(f"{data.date} {data.check_in}", "%Y-%m-%d %H:%M")
        except:
            try:
                check_in_time = datetime.strptime(f"{data.date} {data.check_in}:00", "%Y-%m-%d %H:%M:%S")
            except:
                pass

    check_out_time = None
    if data.check_out:
        try:
            check_out_time = datetime.strptime(f"{data.date} {data.check_out}", "%Y-%m-%d %H:%M")
        except:
            try:
                check_out_time = datetime.strptime(f"{data.date} {data.check_out}:00", "%Y-%m-%d %H:%M:%S")
            except:
                pass

    existing = db.query(AttendanceResult).filter(
        AttendanceResult.employee_id == emp.id,
        AttendanceResult.date == record_date
    ).first()

    result_morning, result_afternoon = classify_manual_attendance(data.status, check_in_time, check_out_time)

    if existing:
        existing.check_in_time = check_in_time
        existing.check_out_time = check_out_time
        existing.result_morning = result_morning
        existing.result_afternoon = result_afternoon
        existing.late_minutes = 0
        existing.early_leave_minutes = 0
        existing.is_full_day_absent = data.status == "旷工" or (not check_in_time and not check_out_time)
        existing.status = "pending"
        existing.updated_at = datetime.now()
    else:
        ar = AttendanceResult(
            employee_id=emp.id,
            date=record_date,
            check_in_time=check_in_time,
            check_out_time=check_out_time,
            result_morning=result_morning,
            result_afternoon=result_afternoon,
            late_minutes=0,
            early_leave_minutes=0,
            is_full_day_absent=data.status == "旷工" or (not check_in_time and not check_out_time),
            status="pending"
        )
        db.add(ar)
    db.commit()
    return {"message": "考勤记录已添加", "employee": emp.name, "date": data.date}

@app.post("/api/attendance/calculate")
def calculate_attendance(start_date: str, end_date: str, employee_id: str = None, db: Session = Depends(get_db)):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")

    if start > end:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")

    employee_filter = None
    if employee_id:
        emp = db.query(Employee).filter((Employee.employee_id == employee_id) | (Employee.id_card == employee_id)).first()
        if emp:
            employee_filter = emp
        elif employee_id:
            raise HTTPException(status_code=404, detail=f"未找到员工: {employee_id}")

    employee_query = db.query(Employee).filter(Employee.is_active == True, Employee.status != "离职")
    if employee_filter:
        employee_query = employee_query.filter(Employee.id == employee_filter.id)
    employees = employee_query.all()

    created_missing = 0
    for emp in employees:
        rules = get_position_rules(db, emp)
        is_rotating = any(r.is_rotating_shift for r in rules)
        for current_date in iter_dates(start, end):
            existing = db.query(AttendanceResult).filter(
                AttendanceResult.employee_id == emp.id,
                AttendanceResult.date == current_date
            ).first()
            if existing:
                continue
            if is_rotating:
                result_morning = "公休"
                result_afternoon = "公休"
                is_absent = False
            else:
                result_morning = "上午缺卡"
                result_afternoon = "下午缺卡"
                is_absent = True
            db.add(AttendanceResult(
                employee_id=emp.id,
                date=current_date,
                result_morning=result_morning,
                result_afternoon=result_afternoon,
                late_minutes=0,
                early_leave_minutes=0,
                is_full_day_absent=is_absent,
                status="pending"
            ))
            created_missing += 1
    if created_missing:
        db.flush()

    query = db.query(AttendanceResult).filter(AttendanceResult.date >= start, AttendanceResult.date <= end)
    if employee_filter:
        query = query.filter(AttendanceResult.employee_id == employee_filter.id)
    records = query.all()
    records_by_key = {(r.employee_id, r.date): r for r in records}
    for record in records:
        if record.check_in_time or not record.check_out_time:
            continue
        if record.check_out_time.date() <= record.date or record.check_out_time.hour >= 12:
            continue
        next_record = records_by_key.get((record.employee_id, record.check_out_time.date()))
        if not next_record or next_record.check_in_time or not next_record.check_out_time:
            continue
        if next_record.check_out_time.date() != record.check_out_time.date() or next_record.check_out_time.hour < 12:
            continue
        next_record.check_in_time = record.check_out_time
        record.check_out_time = None
        record.result_morning = "公休"
        record.result_afternoon = "公休"
        record.late_minutes = 0
        record.early_leave_minutes = 0
        record.is_full_day_absent = False
        record.remarks = "自动修正：次日早卡并入下一工作日"

    processed = 0
    for record in records:
        emp = db.query(Employee).filter(Employee.id == record.employee_id).first()
        if not emp:
            continue
        rules = get_position_rules(db, emp)
        if not record.check_in_time and not record.check_out_time and record.result_morning == "公休" and record.result_afternoon == "公休":
            record.late_minutes = 0
            record.early_leave_minutes = 0
            record.is_full_day_absent = False
            processed += 1
            continue
        if not rules:
            record.result_morning, record.result_afternoon = classify_manual_attendance("正常", record.check_in_time, record.check_out_time)
            record.late_minutes = 0
            record.early_leave_minutes = 0
            record.is_full_day_absent = not record.check_in_time and not record.check_out_time
            record.rule_id = None
            processed += 1
            continue
        
        if not record.check_in_time and record.check_out_time:
            overnight_rules = [r for r in rules if r.is_overnight]
            if overnight_rules:
                rule = overnight_rules[0]
                record.rule_id = rule.id
                actual_out = record.check_out_time.time()
                clean_end = rule.end_time.replace('次日', '').strip()
                rule_end = datetime.strptime(clean_end, "%H:%M").time()
                record.result_morning = "上午缺卡"
                record.late_minutes = 0
                
                if record.check_out_time.hour < 12:
                    rule_end_minutes = rule_end.hour * 60 + rule_end.minute
                    actual_out_minutes = record.check_out_time.hour * 60 + record.check_out_time.minute
                    diff = abs(actual_out_minutes - rule_end_minutes)
                    if diff <= 120:
                        record.result_afternoon = "正常"
                        record.early_leave_minutes = 0
                    else:
                        if actual_out_minutes < rule_end_minutes:
                            early_diff = rule_end_minutes - actual_out_minutes
                            record.early_leave_minutes = early_diff
                            record.result_afternoon = f"早退{early_diff}分钟"
                        else:
                            record.result_afternoon = "正常"
                            record.early_leave_minutes = 0
                else:
                    record.result_afternoon = "正常"
                    record.early_leave_minutes = 0
                
                record.is_full_day_absent = False
                record.remarks = ""
                processed += 1
                continue
        
        best_rule = None
        best_score = float('inf')
        
        is_overnight_shift = False
        if record.check_out_time and record.check_in_time:
            if record.check_out_time.date() > record.check_in_time.date():
                is_overnight_shift = True
            elif record.check_out_time.hour < 12 and record.check_in_time.hour >= 20:
                is_overnight_shift = True
            elif record.check_out_time.hour < record.check_in_time.hour:
                is_overnight_shift = True
        
        for rule in rules:
            try:
                start_h = parse_time_to_hour(rule.start_time)
                end_h = parse_time_to_hour(rule.end_time)
                start_total = parse_rule_time_minutes(rule.start_time)
                end_total_base = parse_rule_time_minutes(rule.end_time)
                is_overnight = rule.is_overnight
                
                score = 0
                
                if record.check_in_time:
                    in_h = record.check_in_time.hour
                    in_m = record.check_in_time.minute
                    in_total = in_h * 60 + in_m
                    score += circular_minute_distance(in_total, start_total)
                
                if record.check_out_time:
                    out_h = record.check_out_time.hour
                    out_m = record.check_out_time.minute
                    out_total = out_h * 60 + out_m
                    if is_overnight:
                        end_total = end_total_base
                        if end_total <= start_total:
                            end_total += 1440
                        if record.check_out_time.date() > record.date or out_total < start_total:
                            out_total += 1440
                        score += abs(out_total - end_total)
                    else:
                        end_total = end_total_base
                        if end_h == 0:
                            end_total = 1440
                        if record.check_out_time.date() > record.date:
                            out_total += 1440
                        if out_h < start_h and out_h >= 12:
                            out_total += 1440
                        score += abs(out_total - end_total)
                
                if score < best_score:
                    best_score = score
                    best_rule = rule
            except:
                continue
        
        if not best_rule:
            if record.check_in_time and record.check_out_time:
                record.result_morning = "正常"
                record.result_afternoon = "正常"
                record.late_minutes = 0
                record.early_leave_minutes = 0
                record.rule_id = None
                processed += 1
            continue
        
        record.rule_id = best_rule.id
        start_h = parse_time_to_hour(best_rule.start_time)
        end_h = parse_time_to_hour(best_rule.end_time)
        start_total = parse_rule_time_minutes(best_rule.start_time)
        end_total_base = parse_rule_time_minutes(best_rule.end_time)
        is_overnight = best_rule.is_overnight

        record.late_minutes = 0
        record.early_leave_minutes = 0

        if record.check_in_time and record.check_out_time:
            in_min = record.check_in_time.hour * 60 + record.check_in_time.minute
            out_min = record.check_out_time.hour * 60 + record.check_out_time.minute
            if in_min == out_min:
                record.result_morning = "待确认"
                record.result_afternoon = "待确认"
                record.remarks = f"上下班打卡时间相同({record.check_in_time.time().strftime('%H:%M')})，需人工确认"
                processed += 1
                continue

        if not record.check_in_time:
            record.result_morning = "上午缺卡"
        else:
            in_h = record.check_in_time.hour
            in_m = record.check_in_time.minute
            in_total = in_h * 60 + in_m

            if is_overnight:
                if start_h >= 20 and in_h < start_h:
                    record.result_morning = "正常"
                else:
                    late = in_total - start_total
                    if late > 0:
                        record.late_minutes = late
                        record.result_morning = f"迟到{late}分钟"
                    else:
                        record.result_morning = "正常"
            else:
                if in_total <= start_total:
                    record.result_morning = "正常"
                else:
                    late = in_total - start_total
                    record.late_minutes = late
                    record.result_morning = f"迟到{late}分钟"
        
        if not record.check_out_time:
            record.result_afternoon = "下午缺卡"
        else:
            out_h = record.check_out_time.hour
            out_m = record.check_out_time.minute
            out_total = out_h * 60 + out_m
            end_total = end_total_base

            if is_overnight:
                if end_total <= start_total:
                    end_total += 1440
                if record.check_out_time.date() > record.date or out_total < start_total:
                    out_total += 1440
                if out_total < end_total:
                    early = end_total - out_total
                    record.early_leave_minutes = early
                    record.result_afternoon = f"早退{early}分钟"
                else:
                    record.result_afternoon = "正常"
                    record.early_leave_minutes = 0
            else:
                if end_h == 0:
                    end_total = 1440
                if record.check_out_time.date() > record.date:
                    out_total += 1440
                if out_total < end_total:
                    early = end_total - out_total
                    if early > 0:
                        record.early_leave_minutes = early
                        record.result_afternoon = f"早退{early}分钟"
                    else:
                        record.result_afternoon = "正常"
                else:
                    record.result_afternoon = "正常"
        
        record.is_full_day_absent = not record.check_in_time and not record.check_out_time
        record.remarks = ""
        processed += 1
    
    db.commit()
    return {"message": f"计算完成，处理了{processed}条记录"}

@app.post("/api/attendance/cleanup-duplicates")
def cleanup_duplicate_attendance(store_id: int = None, db: Session = Depends(get_db)):
    if store_id:
        query = db.query(AttendanceResult).join(Employee, AttendanceResult.employee_id == Employee.id).filter(Employee.store_id == store_id)
    else:
        query = db.query(AttendanceResult)

    subq = db.query(
        AttendanceResult.employee_id,
        AttendanceResult.date,
        func.max(AttendanceResult.id).label('max_id')
    ).group_by(
        AttendanceResult.employee_id,
        AttendanceResult.date
    ).having(func.count(AttendanceResult.id) > 1).subquery()

    duplicates = db.query(AttendanceResult).join(
        subq,
        (AttendanceResult.employee_id == subq.c.employee_id) &
        (AttendanceResult.date == subq.c.date) &
        (AttendanceResult.id != subq.c.max_id)
    ).all()

    deleted_count = 0
    for dup in duplicates:
        db.delete(dup)
        deleted_count += 1

    db.commit()
    return {"message": f"清理完成，删除了{deleted_count}条重复记录"}

@app.delete("/api/attendance/results")
def delete_attendance_results(
    start_date: str,
    end_date: str,
    store_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(AttendanceResult).outerjoin(Employee, AttendanceResult.employee_id == Employee.id).outerjoin(Store, Employee.store_id == Store.id)

    if store_id:
        query = query.filter(Store.id == store_id)
    if start_date:
        query = query.filter(AttendanceResult.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(AttendanceResult.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    results = query.all()
    count = len(results)

    for r in results:
        db.delete(r)

    db.commit()
    return {"message": f"已删除{count}条考勤记录", "deleted": count}

@app.delete("/api/attendance/result/{result_id}")
def delete_single_attendance_result(result_id: int, db: Session = Depends(get_db)):
    result = db.query(AttendanceResult).filter(AttendanceResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="记录不存在")
    emp = db.query(Employee).filter(Employee.id == result.employee_id).first()
    emp_name = emp.name if emp else result.employee_id
    log_operation(db, "管理员", "删除", "考勤记录", result_id, emp_name, f"删除考勤记录：{result.date}")
    db.delete(result)
    db.commit()
    return {"message": "记录已删除"}

@app.get("/api/attendance/results")
def get_attendance_results(
    store_id: int = None,
    position: str = None,
    employee_id: str = None,
    employee_name: str = None,
    start_date: str = None,
    end_date: str = None,
    status: str = None,
    morning: str = None,
    afternoon: str = None,
    abnormal: bool = False,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(AttendanceResult).outerjoin(Employee, AttendanceResult.employee_id == Employee.id).outerjoin(Store, Employee.store_id == Store.id)

    if store_id:
        query = query.filter(Store.id == store_id)
    if position:
        query = query.filter(Employee.position == position)
    if employee_id:
        query = query.filter(Employee.employee_id == employee_id)
    if employee_name:
        query = query.filter(Employee.name.contains(employee_name))
    if start_date:
        query = query.filter(AttendanceResult.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(AttendanceResult.date <= datetime.strptime(end_date, "%Y-%m-%d").date())
    if status:
        query = query.filter(AttendanceResult.status == status)
    if morning:
        query = query.filter(AttendanceResult.result_morning.startswith(morning))
    if afternoon:
        query = query.filter(AttendanceResult.result_afternoon.startswith(afternoon))
    if abnormal:
        query = query.filter(or_(
            AttendanceResult.result_morning != "正常",
            AttendanceResult.result_afternoon != "正常",
            AttendanceResult.late_minutes > 0,
            AttendanceResult.early_leave_minutes > 0,
            AttendanceResult.is_full_day_absent == True,
        ))

    page = max(page, 1)
    page_size = min(max(page_size, 1), 500)
    filtered_records = query.all()
    summary = build_attendance_summary(filtered_records)
    total = len(filtered_records)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    results = query.order_by(AttendanceResult.date, AttendanceResult.id).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "data": [
            {
                "id": r.id,
                "employee_id": r.employee.employee_id if r.employee else '',
                "employee_name": r.employee.name if r.employee else '',
                "store_id": r.employee.store_id if r.employee else 0,
                "store_name": r.employee.store.name if r.employee and r.employee.store else '',
                "position": r.employee.position if r.employee else '',
                "date": r.date.strftime("%Y-%m-%d") if r.date else None,
                "check_in_time": r.check_in_time.strftime("%H:%M:%S") if r.check_in_time else None,
                "check_out_time": r.check_out_time.strftime("%H:%M:%S") if r.check_out_time else None,
                "result_morning": r.result_morning,
                "result_afternoon": r.result_afternoon,
                "late_minutes": r.late_minutes or 0,
                "early_leave_minutes": r.early_leave_minutes or 0,
                "is_full_day_absent": r.is_full_day_absent or False,
                "remarks": r.remarks or "",
                "status": r.status,
                "confirmed_by": r.confirmed_by,
                "confirmed_at": r.confirmed_at.strftime("%Y-%m-%d %H:%M:%S") if r.confirmed_at else None
            }
            for r in results
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "summary": summary
    }

@app.put("/api/attendance/results/{result_id}")
def update_attendance_result(result_id: int, data: AttendanceResultUpdate, db: Session = Depends(get_db)):
    result = db.query(AttendanceResult).filter(AttendanceResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="记录不存在")
    before = {
        "result_morning": result.result_morning,
        "result_afternoon": result.result_afternoon,
        "late_minutes": result.late_minutes,
        "early_leave_minutes": result.early_leave_minutes,
        "remarks": result.remarks,
        "status": result.status,
    }
    
    if data.result_morning is not None:
        result.result_morning = data.result_morning
    if data.result_afternoon is not None:
        result.result_afternoon = data.result_afternoon
    if data.late_minutes is not None:
        result.late_minutes = data.late_minutes
    if data.early_leave_minutes is not None:
        result.early_leave_minutes = data.early_leave_minutes
    if data.remarks is not None:
        result.remarks = data.remarks
    if data.status is not None:
        result.status = data.status
    if data.is_resigned is not None:
        if data.is_resigned:
            result.result_morning = "离职"
            result.result_afternoon = "离职"
            result.remarks = f"员工于{result.date.strftime('%Y-%m-%d')}离职"
            result.status = "confirmed"

            later_records = db.query(AttendanceResult).filter(
                AttendanceResult.employee_id == result.employee_id,
                AttendanceResult.date > result.date
            ).all()
            for later in later_records:
                later.result_morning = "离职"
                later.result_afternoon = "离职"
                later.remarks = f"员工于{result.date.strftime('%Y-%m-%d')}离职"
                later.status = "confirmed"
        else:
            result.result_morning = "正常"
            result.result_afternoon = "正常"
            result.remarks = ""
    if data.confirmed_by is not None:
        result.confirmed_by = data.confirmed_by
        result.status = "confirmed"
        result.confirmed_at = datetime.now()

    after = {
        "result_morning": result.result_morning,
        "result_afternoon": result.result_afternoon,
        "late_minutes": result.late_minutes,
        "early_leave_minutes": result.early_leave_minutes,
        "remarks": result.remarks,
        "status": result.status,
    }
    changed = {k: {"before": before[k], "after": after[k]} for k in before if before[k] != after[k]}
    if changed:
        emp = db.query(Employee).filter(Employee.id == result.employee_id).first()
        operator = data.confirmed_by or data.updated_by or "管理员"
        log_operation(
            db,
            operator,
            "修改",
            "考勤记录",
            result_id,
            emp.name if emp else str(result.employee_id),
            f"{result.date}: " + json.dumps(changed, ensure_ascii=False)
        )
    db.commit()
    return {"message": "记录已更新"}

@app.post("/api/attendance/confirm")
def confirm_attendance_result(result_id: int, confirmed_by: str, db: Session = Depends(get_db)):
    result = db.query(AttendanceResult).filter(AttendanceResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="记录不存在")
    emp = db.query(Employee).filter(Employee.id == result.employee_id).first()
    pos_rule = None
    if emp:
        pos_rule = db.query(PositionAttendanceRule).filter(
            PositionAttendanceRule.position == emp.position,
            PositionAttendanceRule.store_id == emp.store_id
        ).first()
    if not can_confirm_attendance(result, pos_rule):
        raise HTTPException(status_code=400, detail="上下班都缺卡的记录不能被确认")
    emp_name = emp.name if emp else result.employee_id
    log_operation(db, confirmed_by, "确认", "考勤记录", result_id, emp_name, f"确认考勤：{result.date}")
    result.status = "confirmed"
    result.confirmed_by = confirmed_by
    result.confirmed_at = datetime.now()
    db.commit()
    return {"message": "记录已确认"}

@app.post("/api/attendance/batch-confirm-normal")
def batch_confirm_normal(
    store_id: int = None,
    position: str = None,
    employee_id: str = None,
    start_date: str = None,
    end_date: str = None,
    confirmed_by: str = "",
    db: Session = Depends(get_db)
):
    query = db.query(AttendanceResult).outerjoin(Employee, AttendanceResult.employee_id == Employee.id).outerjoin(PositionAttendanceRule, (Employee.position == PositionAttendanceRule.position) & (Employee.store_id == PositionAttendanceRule.store_id))
    query = query.filter(AttendanceResult.result_morning == "正常", AttendanceResult.result_afternoon == "正常", AttendanceResult.status == "pending")
    query = query.filter(
        (AttendanceResult.check_in_time != None) |
        (AttendanceResult.result_morning.in_(["公休", "病假", "事假", "事假两小时"])) |
        (PositionAttendanceRule.is_rotating_shift == True)
    )
    query = query.filter(
        (AttendanceResult.check_out_time != None) |
        (AttendanceResult.result_afternoon.in_(["公休", "病假", "事假", "事假两小时"])) |
        (PositionAttendanceRule.is_rotating_shift == True)
    )
    
    if store_id:
        query = query.filter(Employee.store_id == store_id)
    if position:
        query = query.filter(Employee.position == position)
    if employee_id:
        query = query.filter(Employee.employee_id == employee_id)
    if start_date:
        query = query.filter(AttendanceResult.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(AttendanceResult.date <= datetime.strptime(end_date, "%Y-%m-%d").date())
    
    records = query.all()
    for record in records:
        record.status = "confirmed"
        record.confirmed_by = confirmed_by
        record.confirmed_at = datetime.now()

    log_operation(db, confirmed_by, "批量确认", "考勤记录", None, None, f"批量确认正常：共{len(records)}条记录")
    db.commit()
    return {"confirmed_count": len(records)}

@app.post("/api/attendance/batch-confirm-by-morning")
def batch_confirm_by_morning(
    result_morning: str = None,
    morning: str = None,
    store_id: int = None,
    position: str = None,
    employee_id: str = None,
    start_date: str = None,
    end_date: str = None,
    confirmed_by: str = "",
    db: Session = Depends(get_db)
):
    result_morning = result_morning or morning
    if not result_morning:
        raise HTTPException(status_code=400, detail="请选择上午状态")
    query = db.query(AttendanceResult).outerjoin(Employee, AttendanceResult.employee_id == Employee.id).outerjoin(PositionAttendanceRule, (Employee.position == PositionAttendanceRule.position) & (Employee.store_id == PositionAttendanceRule.store_id))
    query = query.filter(AttendanceResult.result_morning.startswith(result_morning), AttendanceResult.status == "pending")
    query = query.filter(or_(
        AttendanceResult.check_in_time != None,
        AttendanceResult.result_morning.in_(["公休", "病假", "事假", "事假两小时"]),
        PositionAttendanceRule.is_rotating_shift == True
    ))
    query = query.filter(or_(
        AttendanceResult.check_out_time != None,
        AttendanceResult.result_afternoon.in_(["公休", "病假", "事假", "事假两小时"]),
        PositionAttendanceRule.is_rotating_shift == True,
        AttendanceResult.result_afternoon.startswith("正常")
    ))

    if store_id:
        query = query.filter(Employee.store_id == store_id)
    if position:
        query = query.filter(Employee.position == position)
    if employee_id:
        query = query.filter(Employee.employee_id == employee_id)
    if start_date:
        query = query.filter(AttendanceResult.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(AttendanceResult.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    records = query.all()
    for record in records:
        record.status = "confirmed"
        record.confirmed_by = confirmed_by
        record.confirmed_at = datetime.now()

    log_operation(db, confirmed_by, "批量确认", "考勤记录", None, None, f"按上午结果批量确认：{result_morning}，共{len(records)}条记录")
    db.commit()
    return {"confirmed_count": len(records)}

@app.post("/api/attendance/batch-confirm-by-afternoon")
def batch_confirm_by_afternoon(
    result_afternoon: str = None,
    afternoon: str = None,
    store_id: int = None,
    position: str = None,
    employee_id: str = None,
    start_date: str = None,
    end_date: str = None,
    confirmed_by: str = "",
    db: Session = Depends(get_db)
):
    result_afternoon = result_afternoon or afternoon
    if not result_afternoon:
        raise HTTPException(status_code=400, detail="请选择下午状态")
    query = db.query(AttendanceResult).outerjoin(Employee, AttendanceResult.employee_id == Employee.id).outerjoin(PositionAttendanceRule, (Employee.position == PositionAttendanceRule.position) & (Employee.store_id == PositionAttendanceRule.store_id))
    query = query.filter(AttendanceResult.result_afternoon.startswith(result_afternoon), AttendanceResult.status == "pending")
    query = query.filter(or_(
        AttendanceResult.check_out_time != None,
        AttendanceResult.result_afternoon.in_(["公休", "病假", "事假", "事假两小时"]),
        PositionAttendanceRule.is_rotating_shift == True
    ))
    query = query.filter(or_(
        AttendanceResult.check_in_time != None,
        AttendanceResult.result_morning.in_(["公休", "病假", "事假", "事假两小时"]),
        PositionAttendanceRule.is_rotating_shift == True,
        AttendanceResult.result_morning.startswith("正常")
    ))

    if store_id:
        query = query.filter(Employee.store_id == store_id)
    if position:
        query = query.filter(Employee.position == position)
    if employee_id:
        query = query.filter(Employee.employee_id == employee_id)
    if start_date:
        query = query.filter(AttendanceResult.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(AttendanceResult.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    records = query.all()
    for record in records:
        record.status = "confirmed"
        record.confirmed_by = confirmed_by
        record.confirmed_at = datetime.now()

    log_operation(db, confirmed_by, "批量确认", "考勤记录", None, None, f"按下午结果批量确认：{result_afternoon}，共{len(records)}条记录")
    db.commit()
    return {"confirmed_count": len(records)}

@app.post("/api/attendance/mark-resigned")
def mark_employee_resigned(
    employee_id: str,
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    emp = db.query(Employee).filter((Employee.employee_id == employee_id) | (Employee.id_card == employee_id)).first()
    if not emp:
        raise HTTPException(status_code=404, detail="员工不存在")

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误")

    records = db.query(AttendanceResult).filter(
        AttendanceResult.employee_id == emp.id,
        AttendanceResult.date >= start,
        AttendanceResult.date <= end
    ).all()

    for record in records:
        record.result_morning = "离职"
        record.result_afternoon = "离职"
        record.remarks = f"员工于{record.date.strftime('%Y-%m-%d')}离职"
        record.status = "confirmed"

    db.commit()
    return {"message": f"已标记{len(records)}条记录为离职", "updated_count": len(records)}


@app.post("/api/attendance/batch-confirm")
def batch_confirm(data: BatchConfirmRequest, db: Session = Depends(get_db)):
    try:
        start = datetime.strptime(data.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(data.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")

    if start > end:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")

    records = db.query(AttendanceResult).join(Employee, AttendanceResult.employee_id == Employee.id).filter(
        Employee.store_id == data.store_id,
        AttendanceResult.date >= start,
        AttendanceResult.date <= end,
        AttendanceResult.status == "pending",
    ).all()

    for record in records:
        record.status = "confirmed"
        record.confirmed_by = data.confirmed_by
        record.confirmed_at = datetime.now()

    log_operation(db, data.confirmed_by, "批量确认", "考勤记录", None, None, f"按店面日期批量确认：共{len(records)}条记录")
    db.commit()
    return {"confirmed": len(records)}


@app.post("/api/attendance/batch-modify")
def batch_modify_attendance(
    result_morning: str = None,
    result_afternoon: str = None,
    store_id: int = None,
    position: str = None,
    employee_id: str = None,
    employee_name: str = None,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(AttendanceResult).outerjoin(Employee, AttendanceResult.employee_id == Employee.id)

    if store_id:
        query = query.filter(Employee.store_id == store_id)
    if position:
        query = query.filter(Employee.position == position)
    if employee_id:
        query = query.filter(Employee.employee_id == employee_id)
    if employee_name:
        query = query.filter(Employee.name.contains(employee_name))
    if start_date:
        query = query.filter(AttendanceResult.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(AttendanceResult.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    records = query.all()
    count = 0
    for record in records:
        if not record.employee:
            continue
        if result_morning is not None:
            record.result_morning = result_morning
        if result_afternoon is not None:
            record.result_afternoon = result_afternoon
        record.status = "pending"
        count += 1

    db.commit()
    return {"message": f"已批量修改{count}条记录"}

@app.get("/api/attendance/summary")
def get_attendance_summary(
    start_date: str,
    end_date: str,
    period: str = None,
    store_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(AttendanceResult).join(Employee, AttendanceResult.employee_id == Employee.id).join(Store, Employee.store_id == Store.id)

    if store_id:
        query = query.filter(Store.id == store_id)
    if start_date:
        query = query.filter(AttendanceResult.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(AttendanceResult.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    results = query.order_by(AttendanceResult.employee_id, AttendanceResult.date).all()

    emp_resign_date = {}
    for r in results:
        if not r.employee:
            continue
        if r.result_morning == "离职" or r.result_afternoon == "离职":
            emp_id = r.employee_id
            if emp_id not in emp_resign_date:
                emp_resign_date[emp_id] = r.date

    summary = {}
    for r in results:
        if not r.employee:
            continue
        emp_id = r.employee_id

        resign_date = emp_resign_date.get(emp_id)
        if resign_date and r.date > resign_date:
            continue

        if emp_id not in summary:
            summary[emp_id] = {
                "employee_id": r.employee.employee_id,
                "employee_name": r.employee.name,
                "store_name": r.employee.store.name if r.employee and r.employee.store else '',
                "position": r.employee.position,
                "calendar_days": 0,
                "should_public_leave_days": r.employee.public_leave_days or 0,
                "actual_public_leave_days": 0,
                "unpublic_leave_days": 0,
                "overtime_days": 0,
                "normal_days": 0,
                "sick_leave_days": 0,
                "personal_leave_days": 0,
                "personal_leave_2h_count": 0,
                "absent_days": 0,
                "late_days": 0,
                "late_minutes": 0,
                "early_leave_days": 0,
                "early_leave_minutes": 0,
                "forgot_checkin_morning": 0,
                "forgot_checkin_afternoon": 0,
                "missing_count": 0,
                "total_days": 0,
                "is_rotating": False
            }

        is_rotating = False
        pos_rule = db.query(PositionAttendanceRule).filter(
            PositionAttendanceRule.store_id == r.employee.store_id,
            PositionAttendanceRule.position == r.employee.position,
            PositionAttendanceRule.is_active == True
        ).first()
        if pos_rule and pos_rule.is_rotating_shift:
            is_rotating = True

        s = summary[emp_id]
        s["is_rotating"] = is_rotating
        s["total_days"] += 1

        morning = r.result_morning or ""
        afternoon = r.result_afternoon or ""

        late_minutes = result_minutes(morning, "迟到", r.late_minutes or 0)
        early_leave_minutes = result_minutes(afternoon, "早退", r.early_leave_minutes or 0)

        if morning == "正常" and late_minutes <= 0:
            s["normal_days"] += 0.5
        elif is_missing_result(morning):
            s["normal_days"] += 0.5
            s["forgot_checkin_morning"] += 1
            s["missing_count"] += 1
        elif morning == "公休":
            s["actual_public_leave_days"] += 0.5
        elif morning == "病假":
            s["sick_leave_days"] += 0.5
        elif morning == "事假":
            s["personal_leave_days"] += 0.5
        elif morning == "事假两小时":
            s["personal_leave_2h_count"] += 1
        elif is_late_result(morning, late_minutes):
            s["normal_days"] += 0.5
            s["late_days"] += 1
            s["late_minutes"] += late_minutes
        elif morning == "旷工":
            s["absent_days"] += 0.5

        if afternoon == "正常" and early_leave_minutes <= 0:
            s["normal_days"] += 0.5
        elif is_missing_result(afternoon):
            s["normal_days"] += 0.5
            s["forgot_checkin_afternoon"] += 1
            s["missing_count"] += 1
        elif afternoon == "公休":
            s["actual_public_leave_days"] += 0.5
        elif afternoon == "病假":
            s["sick_leave_days"] += 0.5
        elif afternoon == "事假":
            s["personal_leave_days"] += 0.5
        elif afternoon == "事假两小时":
            s["personal_leave_2h_count"] += 1
        elif is_early_result(afternoon, early_leave_minutes):
            s["normal_days"] += 0.5
            s["early_leave_days"] += 1
            s["early_leave_minutes"] += early_leave_minutes
        elif afternoon == "旷工":
            s["absent_days"] += 0.5

    data = []
    for emp_id, s in summary.items():
        s["unpublic_leave_days"] = s["should_public_leave_days"] - s["actual_public_leave_days"]
        if s["unpublic_leave_days"] < 0:
            s["unpublic_leave_days"] = 0
        attendance_with_rest = s["normal_days"] + s["should_public_leave_days"]
        s["salary_calculation_days"] = round(min(s["total_days"], attendance_with_rest), 1)
        s["overtime_days"] = round(max(0, attendance_with_rest - s["total_days"]), 1)
        if s["total_days"] > 0:
            s["attendance_rate"] = round((s["normal_days"] / s["total_days"]) * 100, 1) if s["total_days"] > 0 else 0
        data.append(s)

    data.sort(key=lambda x: x["employee_name"])
    return data


@app.get("/api/attendance/export")
def export_attendance(
    start_date: str,
    end_date: str,
    store_id: int = None,
    db: Session = Depends(get_db)
):
    import pandas as pd
    from fastapi.responses import StreamingResponse
    import io

    query = db.query(AttendanceResult).outerjoin(Employee, AttendanceResult.employee_id == Employee.id).outerjoin(Store, Employee.store_id == Store.id)

    if store_id:
        query = query.filter(Store.id == store_id)
    if start_date:
        query = query.filter(AttendanceResult.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(AttendanceResult.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    results = query.order_by(AttendanceResult.date, Employee.name).all()
    print(f"[EXPORT] Found {len(results)} results, store_id={store_id}, start={start_date}, end={end_date}")

    for r in results:
        print(f"[EXPORT] Record id={r.id}, emp_id={r.employee_id}, date={r.date}, status={r.status}, confirmed_by={r.confirmed_by}, result_morning={r.result_morning}")

    data = []
    for r in results:
        morning = r.result_morning or ""
        afternoon = r.result_afternoon or ""
        sick_leave = 0
        personal_leave = 0
        personal_leave_2h = 0
        absent = 0
        if morning == "病假":
            sick_leave += 0.5
        elif morning == "事假":
            personal_leave += 0.5
        elif morning == "事假两小时":
            personal_leave_2h += 1
        elif morning == "旷工":
            absent += 0.5
        if afternoon == "病假":
            sick_leave += 0.5
        elif afternoon == "事假":
            personal_leave += 0.5
        elif afternoon == "事假两小时":
            personal_leave_2h += 1
        elif afternoon == "旷工":
            absent += 0.5

        data.append({
            "日期": r.date.strftime("%Y-%m-%d") if r.date else "",
            "姓名": r.employee.name if r.employee else "",
            "店面": r.employee.store.name if r.employee and r.employee.store else "",
            "职务": r.employee.position if r.employee else "",
            "上班打卡": r.check_in_time.strftime("%Y-%m-%d %H:%M") if r.check_in_time else "",
            "下班打卡": r.check_out_time.strftime("%Y-%m-%d %H:%M") if r.check_out_time else "",
            "上午考勤": morning,
            "下午考勤": afternoon,
            "病假": sick_leave,
            "事假": personal_leave,
            "事假两小时": personal_leave_2h,
            "旷工": absent,
            "迟到分钟": r.late_minutes or 0,
            "早退分钟": r.early_leave_minutes or 0,
            "备注": r.remarks or ""
        })

    df = pd.DataFrame(data)

    output = io.BytesIO()
    df.to_excel(output, index=False, sheet_name='考勤明细')
    output.seek(0)

    filename = f"attendance_export_{start_date}_{end_date}.xlsx"
    from urllib.parse import quote
    encoded_filename = quote(filename)
    headers = {'Content-Disposition': f'attachment; filename="{filename}"; filename*=UTF-8''{encoded_filename}'}
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=headers
    )

@app.get("/api/attendance/preview-summary")
def preview_attendance_summary(
    start_date: str,
    end_date: str,
    period: str = None,
    store_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(AttendanceResult).outerjoin(Employee, AttendanceResult.employee_id == Employee.id).outerjoin(Store, Employee.store_id == Store.id)

    if store_id:
        query = query.filter(Store.id == store_id)
    if start_date:
        query = query.filter(AttendanceResult.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(AttendanceResult.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    results = query.order_by(AttendanceResult.employee_id, AttendanceResult.date).all()

    emp_resign_date = {}
    for r in results:
        if not r.employee:
            continue
        if r.result_morning == "离职" or r.result_afternoon == "离职":
            emp_id = r.employee_id
            if emp_id not in emp_resign_date:
                emp_resign_date[emp_id] = r.date

    summary = {}
    for r in results:
        if not r.employee:
            continue
        emp_id = r.employee_id

        resign_date = emp_resign_date.get(emp_id)
        if resign_date and r.date > resign_date:
            continue

        if emp_id not in summary:
            is_rotating = False
            pos_rule = db.query(PositionAttendanceRule).filter(
                PositionAttendanceRule.store_id == r.employee.store_id,
                PositionAttendanceRule.position == r.employee.position,
                PositionAttendanceRule.is_active == True
            ).first()
            if pos_rule and pos_rule.is_rotating_shift:
                is_rotating = True

            summary[emp_id] = {
                "姓名": r.employee.name,
                "店面": r.employee.store.name if r.employee and r.employee.store else '',
                "职务": r.employee.position,
                "基本工资": r.employee.base_salary or 0,
                "满勤": r.employee.full_attendance_bonus or 0,
                "补助": r.employee.allowance or 0,
                "工龄": r.employee.work_years or 0,
                "工龄工资": r.employee.seniority_bonus or 0,
                "日历天数": 0,
                "应公休": r.employee.public_leave_days or 0,
                "实公休": 0,
                "未公休": 0,
                "正常": 0,
                "上午缺卡": 0,
                "下午缺卡": 0,
                "未打卡": 0,
                "病假": 0,
                "事假": 0,
                "事假两小时": 0,
                "旷工": 0,
                "迟到": 0,
                "迟到分钟": 0,
                "早退": 0,
                "早退分钟": 0,
                "待确认": 0,
                "离职": 0,
                "出勤率": 0,
                "总天数": 0,
                "is_rotating": is_rotating
            }

        s = summary[emp_id]
        s["总天数"] += 1

        morning = r.result_morning or ""
        afternoon = r.result_afternoon or ""
        late_minutes = result_minutes(morning, "迟到", r.late_minutes or 0)
        early_leave_minutes = result_minutes(afternoon, "早退", r.early_leave_minutes or 0)

        if morning == "正常" and late_minutes <= 0:
            s["正常"] += 0.5
        elif is_missing_result(morning):
            s["正常"] += 0.5
            s["上午缺卡"] += 1
            s["未打卡"] += 1
        elif morning == "公休":
            s["实公休"] += 0.5
        elif morning == "病假":
            s["病假"] += 0.5
        elif morning == "事假":
            s["事假"] += 0.5
        elif morning == "事假两小时":
            s["事假两小时"] += 1
        elif is_late_result(morning, late_minutes):
            s["正常"] += 0.5
            s["迟到"] += 1
            s["迟到分钟"] += late_minutes
        elif morning == "旷工":
            s["旷工"] += 0.5
        elif morning == "离职":
            s["离职"] += 0.5
        elif morning in ["", "待确认"]:
            s["待确认"] += 0.5

        if afternoon == "正常" and early_leave_minutes <= 0:
            s["正常"] += 0.5
        elif is_missing_result(afternoon):
            s["正常"] += 0.5
            s["下午缺卡"] += 1
            s["未打卡"] += 1
        elif afternoon == "公休":
            s["实公休"] += 0.5
        elif afternoon == "病假":
            s["病假"] += 0.5
        elif afternoon == "事假":
            s["事假"] += 0.5
        elif afternoon == "事假两小时":
            s["事假两小时"] += 1
        elif is_early_result(afternoon, early_leave_minutes):
            s["正常"] += 0.5
            s["早退"] += 1
            s["早退分钟"] += early_leave_minutes
        elif afternoon == "旷工":
            s["旷工"] += 0.5
        elif afternoon == "离职":
            s["离职"] += 0.5
        elif afternoon in ["", "待确认"]:
            s["待确认"] += 0.5

    data = []
    for emp_id, s in summary.items():
        s["未公休"] = s["应公休"] - s["实公休"]
        if s["未公休"] < 0:
            s["未公休"] = 0
        if s["总天数"] > 0:
            s["出勤率"] = round((s["正常"] / s["总天数"]) * 100, 1) if s["总天数"] > 0 else 0
        del s["日历天数"]
        del s["总天数"]
        del s["is_rotating"]
        del s["离职"]
        data.append(s)

    data.sort(key=lambda x: x["姓名"])
    return {"data": data, "count": len(data)}

@app.get("/api/attendance/export-summary")
def export_attendance_summary(
    start_date: str,
    end_date: str,
    period: str = None,
    store_id: int = None,
    db: Session = Depends(get_db)
):
    import pandas as pd
    from fastapi.responses import StreamingResponse
    import io

    query = db.query(AttendanceResult).outerjoin(Employee, AttendanceResult.employee_id == Employee.id).outerjoin(Store, Employee.store_id == Store.id)

    if store_id:
        query = query.filter(Store.id == store_id)
    if start_date:
        query = query.filter(AttendanceResult.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(AttendanceResult.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    results = query.order_by(AttendanceResult.employee_id, AttendanceResult.date).all()

    emp_resign_date = {}
    for r in results:
        if not r.employee:
            continue
        if r.result_morning == "离职" or r.result_afternoon == "离职":
            emp_id = r.employee_id
            if emp_id not in emp_resign_date:
                emp_resign_date[emp_id] = r.date

    summary = {}
    for r in results:
        if not r.employee:
            continue
        emp_id = r.employee_id

        resign_date = emp_resign_date.get(emp_id)
        if resign_date and r.date > resign_date:
            continue

        if emp_id not in summary:
            is_rotating = False
            pos_rule = db.query(PositionAttendanceRule).filter(
                PositionAttendanceRule.store_id == r.employee.store_id,
                PositionAttendanceRule.position == r.employee.position,
                PositionAttendanceRule.is_active == True
            ).first()
            if pos_rule and pos_rule.is_rotating_shift:
                is_rotating = True

            summary[emp_id] = {
                "姓名": r.employee.name,
                "店面": r.employee.store.name if r.employee and r.employee.store else '',
                "职务": r.employee.position,
                "基本工资": r.employee.base_salary or 0,
                "满勤": r.employee.full_attendance_bonus or 0,
                "补助": r.employee.allowance or 0,
                "工龄": r.employee.work_years or 0,
                "工龄工资": r.employee.seniority_bonus or 0,
                "日历天数": 0,
                "应公休": r.employee.public_leave_days or 0,
                "实公休": 0,
                "未公休": 0,
                "正常": 0,
                "上午缺卡": 0,
                "下午缺卡": 0,
                "未打卡": 0,
                "病假": 0,
                "事假": 0,
                "事假两小时": 0,
                "旷工": 0,
                "迟到": 0,
                "迟到分钟": 0,
                "早退": 0,
                "早退分钟": 0,
                "待确认": 0,
                "离职": 0,
                "出勤率": 0,
                "总天数": 0,
                "is_rotating": is_rotating
            }

        s = summary[emp_id]
        s["总天数"] += 1

        morning = r.result_morning or ""
        afternoon = r.result_afternoon or ""
        late_minutes = result_minutes(morning, "迟到", r.late_minutes or 0)
        early_leave_minutes = result_minutes(afternoon, "早退", r.early_leave_minutes or 0)

        if morning == "正常" and late_minutes <= 0:
            s["正常"] += 0.5
        elif is_missing_result(morning):
            s["正常"] += 0.5
            s["上午缺卡"] += 1
            s["未打卡"] += 1
        elif morning == "公休":
            s["实公休"] += 0.5
        elif morning == "病假":
            s["病假"] += 0.5
        elif morning == "事假":
            s["事假"] += 0.5
        elif morning == "事假两小时":
            s["事假两小时"] += 1
        elif is_late_result(morning, late_minutes):
            s["正常"] += 0.5
            s["迟到"] += 1
            s["迟到分钟"] += late_minutes
        elif morning == "旷工":
            s["旷工"] += 0.5
        elif morning == "离职":
            s["离职"] += 0.5
        elif morning in ["", "待确认"]:
            s["待确认"] += 0.5

        if afternoon == "正常" and early_leave_minutes <= 0:
            s["正常"] += 0.5
        elif is_missing_result(afternoon):
            s["正常"] += 0.5
            s["下午缺卡"] += 1
            s["未打卡"] += 1
        elif afternoon == "公休":
            s["实公休"] += 0.5
        elif afternoon == "病假":
            s["病假"] += 0.5
        elif afternoon == "事假":
            s["事假"] += 0.5
        elif afternoon == "事假两小时":
            s["事假两小时"] += 1
        elif is_early_result(afternoon, early_leave_minutes):
            s["正常"] += 0.5
            s["早退"] += 1
            s["早退分钟"] += early_leave_minutes
        elif afternoon == "旷工":
            s["旷工"] += 0.5
        elif afternoon == "离职":
            s["离职"] += 0.5
        elif afternoon in ["", "待确认"]:
            s["待确认"] += 0.5

    data = []
    for emp_id, s in summary.items():
        s["未公休"] = s["应公休"] - s["实公休"]
        if s["未公休"] < 0:
            s["未公休"] = 0
        if s["总天数"] > 0:
            s["出勤率"] = round((s["正常"] / s["总天数"]) * 100, 1) if s["总天数"] > 0 else 0
        del s["日历天数"]
        del s["总天数"]
        del s["is_rotating"]
        del s["离职"]
        data.append(s)

    data.sort(key=lambda x: x["姓名"])
    df = pd.DataFrame(data)

    output = io.BytesIO()
    df.to_excel(output, index=False, sheet_name='考勤汇总')
    output.seek(0)

    filename = f"attendance_summary_{start_date}_{end_date}.xlsx"
    from urllib.parse import quote
    encoded_filename = quote(filename)
    headers = {'Content-Disposition': f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'}
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=headers
    )

@app.get("/api/salary/calculate")
def calculate_salary(
    store_id: int = None,
    year: int = None,
    month: int = None,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db)
):
    if (not year or not month) and start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            year = start.year
            month = start.month
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    if not year or not month:
        raise HTTPException(status_code=400, detail="请提供 year/month 或 start_date")
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="月份必须在1-12之间")
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
        if start.year != end.year or start.month != end.month:
            raise HTTPException(status_code=400, detail="工资计算暂只支持同一自然月")

    if store_id:
        store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
        if not store:
            raise HTTPException(status_code=404, detail="店面不存在")
    
    calendar_days = monthrange(year, month)[1]
    
    employee_query = db.query(Employee).filter(Employee.is_active == True)
    if store_id:
        employee_query = employee_query.filter(Employee.store_id == store_id)
    employees = employee_query.all()
    
    salary_rule_by_store = {
        rule.store_id: rule
        for rule in db.query(SalaryRule).filter(SalaryRule.is_active == True).all()
    }

    final_query = db.query(SalaryRecord).filter(
        SalaryRecord.year == year,
        SalaryRecord.month == month,
        SalaryRecord.is_final == True
    )
    if store_id:
        final_query = final_query.filter(SalaryRecord.store_id == store_id)
    final_records = final_query.all()
    if final_records:
        final_store_ids = sorted({r.store_id for r in final_records})
        raise HTTPException(
            status_code=400,
            detail=f"{year}-{month:02d} 工资已最终确认，不能重新计算覆盖；店面ID: {', '.join(str(x) for x in final_store_ids)}"
        )
    
    results = []
    delete_query = db.query(SalaryRecord).filter(
        SalaryRecord.year == year,
        SalaryRecord.month == month
    )
    if store_id:
        delete_query = delete_query.filter(SalaryRecord.store_id == store_id)
    delete_query.delete(synchronize_session=False)
    
    for emp in employees:
        salary_rule = salary_rule_by_store.get(emp.store_id)
        attendance_summary = summarize_employee_attendance(db, emp.id, year, month, confirmed_only=True)
        salary_standard = get_salary_standard_record(db, emp)
        is_full_attendance, _ = evaluate_full_attendance(attendance_summary, salary_standard, calendar_days, salary_rule, emp, year, month)
        full_attendance_bonus_amount = get_full_attendance_bonus(emp, salary_standard, is_full_attendance)

        work_days = attendance_summary["normal_days"]
        late_days = attendance_summary.get("late_days", 0)
        late_events = attendance_summary.get("late_events", [])
        late_minutes = attendance_summary["late_minutes"]
        early_leave_minutes = attendance_summary["early_leave_minutes"]
        absent_days = attendance_summary["absent_days"]
        sick_leave_days = attendance_summary["sick_leave_days"]
        personal_leave_days = attendance_summary["personal_leave_days"]
        personal_leave_2h_count = attendance_summary["personal_leave_2h_count"]
        missing_count = attendance_summary["missing_count"]
        payable_days, overtime_days, employment_days, should_rest_days, is_partial_month = calculate_payable_days(emp, attendance_summary, salary_standard, year, month)
        actual_rest_days = attendance_summary["public_leave_days"]
        
        unpaid_rest_days = max(0, min(should_rest_days, employment_days) - actual_rest_days)
        actual_work_days = payable_days
        
        monthly_base_salary = emp.base_salary or 0
        monthly_allowance = emp.allowance or 0
        monthly_seniority_bonus = emp.seniority_bonus or 0
        salary_ratio = (payable_days / calendar_days) if calendar_days else 0
        base_salary = round(monthly_base_salary * salary_ratio, 2)
        allowance = round(monthly_allowance * salary_ratio, 2)
        seniority_bonus = round(monthly_seniority_bonus * salary_ratio, 2)
        standard_work_days = (salary_standard.standard_work_days if salary_standard and salary_standard.standard_work_days else 22) or 22
        daily_salary = monthly_base_salary / standard_work_days if monthly_base_salary else 0
        
        late_deduct = calculate_late_event_deduct(late_events, salary_rule)
        if late_deduct <= 0:
            late_deduct = calculate_late_deduct(late_minutes, salary_rule)
        late_count_deduct = calculate_threshold_penalty(late_days, getattr(salary_rule, "late_count_penalty_tiers", "") if salary_rule else "")
        
        early_leave_deduct = (early_leave_minutes * (salary_rule.early_leave_deduct_per_minute or 0)) if salary_rule else 0
        absent_deduct = (absent_days * daily_salary * (salary_rule.absent_multiplier or 2)) if salary_rule else 0
        if salary_rule and absent_days > 0:
            absent_deduct += (getattr(salary_rule, "absent_extra_penalty", 0) or 0)
        sick_leave_deduct = 0
        personal_leave_deduct = personal_leave_days * daily_salary * ((salary_rule.personal_leave_deduct_per_day or 2) if salary_rule else 2)
        personal_leave_2h_deduct = personal_leave_2h_count * ((getattr(salary_rule, "personal_leave_2h_deduct", 0) or 0) if salary_rule else 0)
        missing_tiers = getattr(salary_rule, "missing_deduct_tiers", "") if salary_rule else ""
        missing_deduct = calculate_count_tier_deduct(missing_count, missing_tiers)
        if missing_deduct <= 0:
            missing_deduct = missing_count * ((getattr(salary_rule, "missing_check_deduct", 0) or 0) if salary_rule else 0)
        overtime_pay = round(overtime_days * (monthly_base_salary / calendar_days if calendar_days else 0), 2)
        
        total_deduct = late_deduct + late_count_deduct + early_leave_deduct + absent_deduct + sick_leave_deduct + personal_leave_deduct + personal_leave_2h_deduct + missing_deduct
        gross_salary = base_salary + allowance + seniority_bonus + full_attendance_bonus_amount + overtime_pay
        actual_salary = max(0, gross_salary - total_deduct)
        
        salary_record = SalaryRecord(
            store_id=emp.store_id,
            employee_id=emp.id,
            year=year,
            month=month,
            base_salary=base_salary,
            full_attendance_bonus=full_attendance_bonus_amount,
            allowance=allowance,
            seniority_bonus=seniority_bonus,
            overtime_pay=overtime_pay,
            work_days=actual_work_days,
            actual_work_days=work_days,
            late_minutes=late_minutes,
            early_leave_minutes=early_leave_minutes,
            absent_days=absent_days,
            sick_leave_days=sick_leave_days,
            personal_leave_days=personal_leave_days,
            personal_leave_2h_count=personal_leave_2h_count,
            missing_count=missing_count,
            late_deduct=late_deduct,
            late_count_deduct=late_count_deduct,
            early_leave_deduct=early_leave_deduct,
            absent_deduct=absent_deduct,
            sick_leave_deduct=sick_leave_deduct,
            personal_leave_deduct=personal_leave_deduct,
            personal_leave_2h_deduct=personal_leave_2h_deduct,
            missing_deduct=missing_deduct,
            total_deduct=total_deduct,
            total_salary=actual_salary,
            is_full_attendance=is_full_attendance,
            is_final=False
        )
        db.add(salary_record)
        
        results.append({
            "employee_id": emp.employee_id,
            "employee_name": emp.name,
            "store_id": emp.store_id,
            "store_name": emp.store.name if emp.store else "",
            "position": emp.position,
            "base_salary": base_salary,
            "allowance": allowance,
            "seniority_bonus": seniority_bonus,
            "overtime_pay": overtime_pay,
            "full_attendance_bonus": full_attendance_bonus_amount,
            "is_full_attendance": is_full_attendance,
            "calendar_days": calendar_days,
            "should_rest_days": should_rest_days,
            "actual_rest_days": actual_rest_days,
            "unpaid_rest_days": unpaid_rest_days,
            "actual_work_days": actual_work_days,
            "employment_days": employment_days,
            "overtime_days": overtime_days,
            "is_partial_month": is_partial_month,
            "work_days": work_days,
            "standard_work_days": standard_work_days,
            "late_days": late_days,
            "late_minutes": late_minutes,
            "early_leave_minutes": early_leave_minutes,
            "absent_days": absent_days,
            "sick_leave_days": sick_leave_days,
            "personal_leave_days": personal_leave_days,
            "personal_leave_2h_count": personal_leave_2h_count,
            "missing_count": missing_count,
            "late_deduct": late_deduct,
            "late_count_deduct": late_count_deduct,
            "early_leave_deduct": early_leave_deduct,
            "absent_deduct": absent_deduct,
            "sick_leave_deduct": sick_leave_deduct,
            "personal_leave_deduct": personal_leave_deduct,
            "personal_leave_2h_deduct": personal_leave_2h_deduct,
            "missing_deduct": missing_deduct,
            "total_deduct": total_deduct,
            "total_salary": actual_salary,
            "is_final": False
        })
    
    db.commit()
    return {"message": f"工资计算完成", "results": results}

@app.post("/api/salary/finalize")
def finalize_salary(
    store_id: int = None,
    year: int = None,
    month: int = None,
    start_date: str = None,
    confirmed_by: str = "管理员",
    db: Session = Depends(get_db)
):
    if (not year or not month) and start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            year = start.year
            month = start.month
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    if not year or not month:
        raise HTTPException(status_code=400, detail="请提供 year/month 或 start_date")
    if store_id:
        store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
        if not store:
            raise HTTPException(status_code=404, detail="店面不存在")

    first_day, last_day = month_range(year, month)
    pending_attendance_query = db.query(AttendanceResult).join(Employee, AttendanceResult.employee_id == Employee.id).filter(
        AttendanceResult.date >= first_day,
        AttendanceResult.date <= last_day,
        AttendanceResult.status != "confirmed"
    )
    if store_id:
        pending_attendance_query = pending_attendance_query.filter(Employee.store_id == store_id)
    pending_attendance_count = pending_attendance_query.count()
    if pending_attendance_count:
        raise HTTPException(status_code=400, detail=f"还有 {pending_attendance_count} 条考勤未确认，不能最终确认工资")

    query = db.query(SalaryRecord).filter(
        SalaryRecord.year == year,
        SalaryRecord.month == month
    )
    if store_id:
        query = query.filter(SalaryRecord.store_id == store_id)
    records = query.all()
    if not records:
        raise HTTPException(status_code=404, detail="没有可确认的工资记录，请先计算工资")

    now = datetime.now()
    for record in records:
        record.is_final = True
        record.confirmed_by = confirmed_by or "管理员"
        record.confirmed_at = now

    target_name = f"{year}-{month:02d}" + (f" 店面{store_id}" if store_id else " 全部店面")
    log_operation(db, confirmed_by or "管理员", "最终确认", "工资记录", None, target_name, f"最终确认工资记录 {len(records)} 条")
    db.commit()
    return {
        "message": "工资已最终确认",
        "confirmed": len(records),
        "year": year,
        "month": month,
        "store_id": store_id
    }

@app.get("/api/salary/records", response_model=List[dict])
def get_salary_records(store_id: int = None, year: int = None, month: int = None, db: Session = Depends(get_db)):
    query = db.query(SalaryRecord).join(Employee, SalaryRecord.employee_id == Employee.id)
    
    if store_id:
        query = query.filter(SalaryRecord.store_id == store_id)
    if year:
        query = query.filter(SalaryRecord.year == year)
    if month:
        query = query.filter(SalaryRecord.month == month)
    
    records = query.order_by(Employee.name, SalaryRecord.year, SalaryRecord.month).all()
    
    return [
        {
            "id": r.id,
            "employee_id": r.employee.employee_id if r.employee else '',
            "employee_name": r.employee.name if r.employee else '',
            "position": r.employee.position if r.employee else '',
            "year": r.year,
            "month": r.month,
            "base_salary": r.base_salary,
            "allowance": r.allowance,
            "seniority_bonus": r.seniority_bonus,
            "overtime_pay": r.overtime_pay,
            "full_attendance_bonus": r.full_attendance_bonus,
            "is_full_attendance": r.is_full_attendance,
            "is_final": r.is_final,
            "confirmed_by": r.confirmed_by or "",
            "confirmed_at": r.confirmed_at.strftime("%Y-%m-%d %H:%M:%S") if r.confirmed_at else "",
            "work_days": r.work_days,
            "actual_work_days": r.actual_work_days,
            "late_minutes": r.late_minutes,
            "early_leave_minutes": r.early_leave_minutes,
            "absent_days": r.absent_days,
            "sick_leave_days": r.sick_leave_days,
            "personal_leave_days": r.personal_leave_days,
            "personal_leave_2h_count": r.personal_leave_2h_count,
            "missing_count": r.missing_count,
            "late_deduct": r.late_deduct,
            "late_count_deduct": getattr(r, "late_count_deduct", 0) or 0,
            "early_leave_deduct": r.early_leave_deduct,
            "absent_deduct": r.absent_deduct,
            "sick_leave_deduct": r.sick_leave_deduct,
            "personal_leave_deduct": r.personal_leave_deduct,
            "personal_leave_2h_deduct": r.personal_leave_2h_deduct,
            "missing_deduct": getattr(r, "missing_deduct", 0) or 0,
            "total_deduct": r.total_deduct,
            "total_salary": r.total_salary,
            "actual_salary": r.total_salary
        }
        for r in records
    ]

if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8010)
    except ImportError:
        print("uvicorn 未安装，尝试使用 Python 内置服务器...")
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8010)
