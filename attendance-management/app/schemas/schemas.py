from pydantic import BaseModel, validator
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


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


class SalaryRuleCreate(BaseModel):
    store_id: int
    late_deduct_tiers: str = ""
    early_leave_deduct_per_minute: float = 0
    absent_multiplier: float = 2
    sick_leave_deduct_per_day: float = 1
    personal_leave_deduct_per_day: float = 2
    personal_leave_2h_deduct: float = 0


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
