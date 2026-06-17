"""
模块化迁移草稿入口。

当前项目已冻结根目录 main.py 为本地测试运行入口：
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

不要使用 uvicorn app.main:app 进行业务测试；本文件尚未同步完整的考勤、
工资核算、工资审计、最终确认等规则。
"""

import secrets
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from config import get_settings
from app.models import (
    Base,
    engine,
    SessionLocal,
    get_db,
    Store,
    OperationLog,
    Employee,
    AttendanceRecord,
    LeaveRequest,
    SalaryRecord,
    AttendanceSettings,
    PositionAttendanceRule,
    AttendanceResult,
    SalaryRule,
    SalaryStandard,
    SalaryImportBatch,
    SalaryDraft,
    SalaryAuditResult,
    User,
    init_default_settings
)
from app.schemas import (
    LoginRequest,
    RegisterRequest,
    AttendanceResultUpdate,
    ManualAttendanceCreate,
    StoreCreate,
    PositionRuleCreate,
    SalaryRuleCreate,
    SalaryStandardCreate,
    BatchConfirmRequest,
    SalaryAuditReviewRequest,
    EmployeeCreate,
    EmployeeUpdate
)
from app.utils import (
    parse_money,
    first_existing,
    normalize_header_text,
    load_salary_draft_dataframe,
    month_range_func,
    can_confirm_attendance,
    build_attendance_summary,
    pick_standard_value,
    pick_standard_max,
    parse_time_to_hour
)
from security import hash_password, verify_password

settings = get_settings()
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# Rate limiting storage
rate_limit_storage = {}
login_attempts = {}

# Add CORS middleware
cors_origins = settings.CORS_ORIGINS
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# Global exception handlers
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
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Helper functions
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


def get_client_ip(request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Startup event
@app.on_event("startup")
def startup_event():
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    init_default_settings()
    # Check for personal_leave_2h_deduct column
    try:
        with engine.begin() as conn:
            result = conn.exec_driver_sql("SHOW COLUMNS FROM salary_rules LIKE 'personal_leave_2h_deduct'")
            if not result.fetchone():
                conn.exec_driver_sql("ALTER TABLE salary_rules ADD COLUMN personal_leave_2h_deduct FLOAT DEFAULT 0")
    except Exception as e:
        print(f"工资规则字段检查失败: {e}")


# Root endpoint
@app.get("/")
async def root():
    return FileResponse("index.html", media_type="text/html")


# Auth endpoints
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
def login_endpoint(data: LoginRequest, db: Session = Depends(get_db)):
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


# Login endpoint (keep the existing one)
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
        login_attempts[client_ip]["locked_until"] = datetime.now() + datetime.timedelta(minutes=15)
        return {"success": False, "message": "登录失败次数过多，请15分钟后再试"}
    return {"success": False, "message": "用户名或密码错误"}


# Store endpoints
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
        log_operation(db, "系统", "修改", "店面", existing.id, existing.name, "更新店面信息")
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


# Logs endpoint
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


# Employees endpoints
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
    return [{
        "id": e.id, "employee_id": e.employee_id, "name": e.name, "id_card": e.id_card,
        "position": e.position, "store_id": e.store_id, "store_name": e.store.name if e.store else "-",
        "base_salary": e.base_salary or 0, "hourly_rate": e.hourly_rate or 0,
        "phone": e.phone or "",
        "hire_date": e.hire_date.isoformat() if e.hire_date else None,
        "status": e.status or "在职", "probation": e.probation or False,
        "work_years": e.work_years or 0, "seniority_bonus": e.seniority_bonus or 0,
        "full_attendance_bonus": e.full_attendance_bonus or 0,
        "allowance": e.allowance or 0, "public_leave_days": e.public_leave_days or 0,
        "is_active": e.is_active
    } for e in employees]


@app.get("/api/positions")
def get_positions(store_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Employee.position).distinct()
    if store_id:
        query = query.filter(Employee.store_id == store_id)
    positions = [p[0] for p in query.all() if p[0]]
    positions.sort()
    return positions


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
    if existing:
        existing.name = data.name
        existing.id_card = data.id_card
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
                from datetime import datetime as dt
                existing.hire_date = dt.strptime(data.hire_date, "%Y-%m-%d").date()
            except:
                pass
        db.commit()
        return {"message": "员工已更新", "id": existing.id}
    employee = Employee(
        store_id=data.store_id,
        employee_id=data.employee_id,
        name=data.name,
        id_card=data.id_card,
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
            from datetime import datetime as dt
            employee.hire_date = dt.strptime(data.hire_date, "%Y-%m-%d").date()
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
    employee.id_card = data.id_card if data.id_card else None
    employee.position = data.position
    employee.phone = data.phone
    if data.hire_date:
        from datetime import datetime as dt
        employee.hire_date = dt.strptime(data.hire_date, "%Y-%m-%d").date()
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


# Export/Import endpoints
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

    headers = {'Content-Disposition': 'attachment; filename*=UTF-8\'\'%E5%B7%A5%E8%B5%84%E5%B7%A5%E6%81%AF%E6%A0%BC%E5%BC%8F.xlsx'}
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
                skipped_details.append(f"行{idx + 2}: 姓名为空")
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
            skipped_details.append(f"行{idx + 2}: {str(e)}")
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


# Salary rules endpoints
@app.get("/api/salary-rules", response_model=List[dict])
def get_salary_rules(store_id: int = None, db: Session = Depends(get_db)):
    query = db.query(SalaryRule).filter(SalaryRule.is_active == True)
    if store_id:
        query = query.filter(SalaryRule.store_id == store_id)
    rules = query.all()
    return [{"id": r.id, "store_id": r.store_id, "late_deduct_tiers": r.late_deduct_tiers,
             "early_leave_deduct_per_minute": r.early_leave_deduct_per_minute,
             "absent_multiplier": r.absent_multiplier,
             "sick_leave_deduct_per_day": r.sick_leave_deduct_per_day,
             "personal_leave_deduct_per_day": r.personal_leave_deduct_per_day,
             "personal_leave_2h_deduct": getattr(r, "personal_leave_2h_deduct", 0) or 0,
             "is_active": r.is_active} for r in rules]


@app.post("/api/salary-rules")
def create_salary_rule(data: SalaryRuleCreate, db: Session = Depends(get_db)):
    rule = SalaryRule(
        store_id=data.store_id,
        late_deduct_tiers=data.late_deduct_tiers,
        early_leave_deduct_per_minute=data.early_leave_deduct_per_minute,
        absent_multiplier=data.absent_multiplier,
        sick_leave_deduct_per_day=data.sick_leave_deduct_per_day,
        personal_leave_deduct_per_day=data.personal_leave_deduct_per_day,
        personal_leave_2h_deduct=data.personal_leave_2h_deduct
    )
    db.add(rule)
    db.commit()
    return {"message": "薪资规则创建成功", "id": rule.id}


# Salary standards endpoints
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
    standard.description = data.description
    standard.is_active = True
    log_operation(db, "系统", "修改", "工资标准", standard.id, standard.position, "修改店面岗位工资标准")
    db.commit()
    return {"message": "工资标准已修改", "id": standard_id}


@app.delete("/api/salary-standards/{standard_id}")
def delete_salary_standard(standard_id: int, db: Session = Depends(get_db)):
    standard = db.query(SalaryStandard).filter(SalaryStandard.id == standard_id).first()
    if not standard:
        raise HTTPException(status_code=404, detail="工资标准不存在")
    standard.is_active = False
    log_operation(db, "系统", "删除", "工资标准", standard.id, standard.position, "停用店面岗位工资标准")
    db.commit()
    return {"message": "工资标准已删除"}


# Sync endpoints
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


# Salary sync function
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


# Salary audit function
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


def summarize_employee_attendance(db, employee_id, year, month):
    start, end = month_range_func(year, month)
    records = db.query(AttendanceResult).filter(
        AttendanceResult.employee_id == employee_id,
        AttendanceResult.date >= start,
        AttendanceResult.date <= end
    ).all()
    summary = {
        "records": len(records),
        "normal_days": 0,
        "late_minutes": 0,
        "early_leave_minutes": 0,
        "missing_count": 0,
        "sick_leave_days": 0,
        "personal_leave_days": 0,
        "personal_leave_2h_count": 0,
        "absent_days": 0,
        "public_leave_days": 0,
        "is_resigned": False,
    }
    for r in records:
        morning = r.result_morning or ""
        afternoon = r.result_afternoon or ""
        summary["late_minutes"] += r.late_minutes or 0
        summary["early_leave_minutes"] += r.early_leave_minutes or 0
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
    return summary


def run_salary_audit(db, batch_id):
    batch = db.query(SalaryImportBatch).filter(SalaryImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="工资批次不存在")

    db.query(SalaryAuditResult).filter(SalaryAuditResult.batch_id == batch_id).delete()
    drafts = db.query(SalaryDraft).filter(SalaryDraft.batch_id == batch_id).all()
    start, end = month_range_func(batch.year, batch.month)

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
        total_deduction = draft.deduction or 0
        has_deduction_or_remark = total_deduction > 0 or bool((draft.remark or "").strip())

        if (emp.status == "离职" or not emp.is_active or att["is_resigned"]) and draft.net_salary > 0:
            add_salary_audit(db, batch_id, "RESIGNED_WITH_SALARY", "离职员工仍有工资", "critical", f"{emp.name} 已离职或考勤标记离职，但实发工资 {draft.net_salary}", draft=draft, employee=emp)
        if emp.hire_date and emp.hire_date > end and draft.net_salary > 0:
            add_salary_audit(db, batch_id, "HIRED_AFTER_MONTH", "入职晚于工资月份", "critical", f"{emp.name} 入职日期 {emp.hire_date} 晚于工资月份，但有工资 {draft.net_salary}", draft=draft, employee=emp)
        if att["absent_days"] > 0 and not has_deduction_or_remark:
            add_salary_audit(db, batch_id, "ABSENT_NO_DEDUCTION", "旷工无扣款或备注", "critical", f"{emp.name} 本月旷工 {att['absent_days']} 天，工资表无扣款/备注", draft=draft, employee=emp)
        if (att["personal_leave_days"] > 0 or att["sick_leave_days"] > 0) and not has_deduction_or_remark:
            add_salary_audit(db, batch_id, "LEAVE_NO_DEDUCTION", "请假无扣款或备注", "warning", f"{emp.name} 病假 {att['sick_leave_days']} 天、事假 {att['personal_leave_days']} 天，工资表无扣款/备注", draft=draft, employee=emp)
        if att["personal_leave_2h_count"] > 0 and not has_deduction_or_remark:
            add_salary_audit(db, batch_id, "PERSONAL_LEAVE_2H_NO_DEDUCTION", "事假两小时无扣款或备注", "warning", f"{emp.name} 事假两小时 {att['personal_leave_2h_count']} 次，工资表无扣款/备注", draft=draft, employee=emp)
        if (att["late_minutes"] > 0 or att["early_leave_minutes"] > 0) and not has_deduction_or_remark:
            add_salary_audit(db, batch_id, "LATE_EARLY_NO_DEDUCTION", "迟到早退无扣款或备注", "warning", f"{emp.name} 迟到 {att['late_minutes']} 分钟、早退 {att['early_leave_minutes']} 分钟，工资表无扣款/备注", draft=draft, employee=emp)
        if att["missing_count"] >= 3 and draft.full_attendance_bonus > 0:
            add_salary_audit(db, batch_id, "MISSING_WITH_FULL_BONUS", "缺卡较多仍发满勤", "warning", f"{emp.name} 缺卡/待确认 {att['missing_count']} 次，但满勤奖 {draft.full_attendance_bonus}", draft=draft, employee=emp)
        if (att["absent_days"] > 0 or att["personal_leave_days"] > 0 or att["personal_leave_2h_count"] > 0 or att["sick_leave_days"] > 0 or att["late_minutes"] > 0 or att["early_leave_minutes"] > 0) and draft.full_attendance_bonus > 0:
            add_salary_audit(db, batch_id, "NOT_FULL_ATTENDANCE_BONUS", "未满勤但发满勤奖", "warning", f"{emp.name} 存在异常考勤，但满勤奖 {draft.full_attendance_bonus}", draft=draft, employee=emp)

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
