#!/usr/bin/env python3
from models import SessionLocal, Employee, SalaryStandard

db = SessionLocal()

print("=== 员工工资信息 ===")
employees = db.query(Employee).all()
for emp in employees:
    print(f"{emp.name} ({emp.position}):")
    print(f"  基本工资: {emp.base_salary}")
    print(f"  全勤奖: {emp.full_attendance_bonus}")
    print(f"  补助: {emp.allowance}")
    print(f"  公休天数: {emp.public_leave_days}")
    print()

print("=== 现有工资标准 ===")
standards = db.query(SalaryStandard).all()
for std in standards:
    print(f"{std.position} ({std.store_id}):")
    print(f"  基本工资: {std.base_salary}")
    print(f"  全勤奖: {std.full_attendance_bonus}")
    print(f"  补助: {std.allowance}")
    print()

db.close()
