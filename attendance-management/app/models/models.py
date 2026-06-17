from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Index, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base, SessionLocal


class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    city = Column(String(100), default="")
    address = Column(String(500), default="")
    manager = Column(String(100), default="")
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class OperationLog(Base):
    __tablename__ = "operation_logs"
    id = Column(Integer, primary_key=True, index=True)
    operator = Column(String(100), default="系统")
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(Integer, nullable=True)
    target_name = Column(String(200), nullable=True)
    details = Column(String(1000), default="")
    ip_address = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.now)


class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, index=True, nullable=False)
    id_card = Column(String(18), unique=True, index=True, nullable=True)
    name = Column(String(100), nullable=False)
    former_names = Column(String(500), default="")
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    position = Column(String(100), default="")
    shift = Column(String(50), default="常日班")
    base_salary = Column(Float, default=0.0)
    hourly_rate = Column(Float, default=0.0)
    full_attendance_bonus = Column(Float, default=0.0)
    allowance = Column(Float, default=0.0)
    public_leave_days = Column(Float, default=0.0)
    work_years = Column(Float, default=0.0)
    seniority_bonus = Column(Float, default=0.0)
    phone = Column(String(20), default="")
    hire_date = Column(Date, nullable=True)
    probation = Column(Boolean, default=True)
    status = Column(String(20), default="在职")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    store = relationship("Store")
    attendance_records = relationship("AttendanceRecord", back_populates="employee")
    salary_records = relationship("SalaryRecord", back_populates="employee")
    leave_requests = relationship("LeaveRequest", back_populates="employee")
    attendance_results = relationship("AttendanceResult", back_populates="employee")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    work_hours = Column(Float, default=0.0)
    overtime_hours = Column(Float, default=0.0)
    status = Column(String(20), default="normal")
    created_at = Column(DateTime, default=datetime.now)
    employee = relationship("Employee", back_populates="attendance_records")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(String(500), default="")
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.now)
    employee = relationship("Employee", back_populates="leave_requests")


class SalaryRecord(Base):
    __tablename__ = "salary_records"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    base_salary = Column(Float, default=0.0)
    overtime_pay = Column(Float, default=0.0)
    bonus = Column(Float, default=0.0)
    deduction = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    late_deduction = Column(Float, default=0.0)
    absence_deduction = Column(Float, default=0.0)
    total_salary = Column(Float, default=0.0)
    work_days = Column(Integer, default=0)
    actual_work_days = Column(Integer, default=0)
    leave_days = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    employee = relationship("Employee", back_populates="salary_records")


class AttendanceSettings(Base):
    __tablename__ = "attendance_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(500), nullable=False)
    description = Column(String(500), default="")


class PositionAttendanceRule(Base):
    __tablename__ = "position_attendance_rules"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    position = Column(String(100), nullable=False, index=True)
    shift = Column(String(50), default="常日班")
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    is_overnight = Column(Boolean, default=False)
    base_salary = Column(Float, default=0)
    full_attendance_bonus = Column(Float, default=0)
    allowance = Column(Float, default=0)
    public_leave_days = Column(Float, default=0)
    work_days_per_month = Column(Float, default=0)
    is_rotating_shift = Column(Boolean, default=False)
    seniority_bonus = Column(Float, default=0)
    description = Column(String(500), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    store = relationship("Store")

    __table_args__ = (
        Index('idx_store_position_shift', 'store_id', 'position', 'shift'),
    )


class AttendanceResult(Base):
    __tablename__ = "attendance_results"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    rule_id = Column(Integer, ForeignKey("position_attendance_rules.id"), nullable=True)
    result_morning = Column(String(50), default="正常")
    result_afternoon = Column(String(50), default="正常")
    late_minutes = Column(Integer, default=0)
    early_leave_minutes = Column(Integer, default=0)
    is_full_day_absent = Column(Boolean, default=False)
    remarks = Column(String(500), default="")
    status = Column(String(20), default="pending")
    confirmed_by = Column(String(100), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    employee = relationship("Employee", back_populates="attendance_results")
    rule = relationship("PositionAttendanceRule")

    __table_args__ = (
        Index('idx_employee_date', 'employee_id', 'date'),
    )


class SalaryRule(Base):
    __tablename__ = "salary_rules"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    base_salary = Column(Float, default=0)
    late_deduct_tiers = Column(String(255), default="")
    early_leave_deduct_per_minute = Column(Float, default=0)
    absent_multiplier = Column(Float, default=2)
    sick_leave_deduct_per_day = Column(Float, default=1)
    personal_leave_deduct_per_day = Column(Float, default=2)
    personal_leave_2h_deduct = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SalaryStandard(Base):
    __tablename__ = "salary_standards"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    position = Column(String(100), nullable=False, index=True)
    base_salary = Column(Float, default=0)
    full_attendance_bonus = Column(Float, default=0)
    allowance = Column(Float, default=0)
    public_leave_days = Column(Float, default=0)
    standard_work_days = Column(Float, default=0)
    min_net_salary = Column(Float, default=0)
    max_net_salary = Column(Float, default=0)
    description = Column(String(500), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    store = relationship("Store")

    __table_args__ = (
        Index('idx_salary_standard_store_position', 'store_id', 'position'),
    )


class SalaryImportBatch(Base):
    __tablename__ = "salary_import_batches"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    file_name = Column(String(255), default="")
    uploaded_by = Column(String(100), default="")
    row_count = Column(Integer, default=0)
    total_net_salary = Column(Float, default=0)
    status = Column(String(20), default="imported")
    created_at = Column(DateTime, default=datetime.now)
    store = relationship("Store")


class SalaryDraft(Base):
    __tablename__ = "salary_drafts"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("salary_import_batches.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    raw_employee_id = Column(String(50), default="")
    raw_id_card = Column(String(18), default="")
    employee_name = Column(String(100), nullable=False, index=True)
    store_name = Column(String(100), default="")
    position = Column(String(100), default="")
    base_salary = Column(Float, default=0)
    commission = Column(Float, default=0)
    bonus = Column(Float, default=0)
    allowance = Column(Float, default=0)
    full_attendance_bonus = Column(Float, default=0)
    deduction = Column(Float, default=0)
    net_salary = Column(Float, default=0)
    remark = Column(String(500), default="")
    raw_data = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    batch = relationship("SalaryImportBatch")
    employee = relationship("Employee")

    __table_args__ = (
        Index('idx_salary_batch_name', 'batch_id', 'employee_name'),
    )


class SalaryAuditResult(Base):
    __tablename__ = "salary_audit_results"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("salary_import_batches.id"), nullable=False, index=True)
    draft_id = Column(Integer, ForeignKey("salary_drafts.id"), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    rule_code = Column(String(80), nullable=False, index=True)
    rule_name = Column(String(120), nullable=False)
    severity = Column(String(20), default="warning", index=True)
    description = Column(String(1000), default="")
    status = Column(String(20), default="pending", index=True)
    reviewer = Column(String(100), nullable=True)
    review_note = Column(String(500), default="")
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    batch = relationship("SalaryImportBatch")
    draft = relationship("SalaryDraft")
    employee = relationship("Employee")

    __table_args__ = (
        Index('idx_salary_audit_batch_status', 'batch_id', 'status'),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


def init_default_settings():
    db = SessionLocal()
    try:
        if not db.query(AttendanceSettings).first():
            settings = [
                AttendanceSettings(key="work_start_time", value="09:00", description="上班时间"),
                AttendanceSettings(key="work_end_time", value="18:00", description="下班时间"),
                AttendanceSettings(key="late_threshold", value="09:30", description="迟到阈值"),
                AttendanceSettings(key="early_leave_threshold", value="17:30", description="早退阈值"),
                AttendanceSettings(key="overtime_rate", value="1.5", description="加班费率"),
                AttendanceSettings(key="monthly_work_days", value="22", description="每月工作天数"),
            ]
            for s in settings:
                db.add(s)
            db.commit()
    finally:
        db.close()
