#!/usr/bin/env python3
"""
测试数据生成脚本
用于生成两人的实际测试数据
"""
import sys
from datetime import datetime, date, timedelta
from models import (
    SessionLocal, Base, engine,
    Store, Employee, AttendanceRecord, LeaveRequest, SalaryRecord,
    PositionAttendanceRule, SalaryStandard, User, AttendanceSettings,
    init_default_settings
)
from security import hash_password


def init_test_data():
    """初始化测试数据"""
    db = SessionLocal()
    try:
        print("正在初始化测试数据...")
        
        # 初始化默认设置
        init_default_settings()
        
        # 创建店面
        store1 = Store(code="ST001", name="朝阳门店", city="北京", address="朝阳区建国路88号", manager="张经理")
        store2 = Store(code="ST002", name="海淀门店", city="北京", address="海淀区中关村大街1号", manager="李经理")
        db.add(store1)
        db.add(store2)
        db.flush()
        
        # 创建岗位考勤规则
        rules = [
            PositionAttendanceRule(
                store_id=store1.id, position="店长", shift="常日班",
                start_time="09:00", end_time="18:00",
                base_salary=8000, full_attendance_bonus=500, allowance=1000,
                public_leave_days=8, work_days_per_month=22
            ),
            PositionAttendanceRule(
                store_id=store1.id, position="导购", shift="常日班",
                start_time="09:00", end_time="18:00",
                base_salary=4000, full_attendance_bonus=300, allowance=500,
                public_leave_days=5, work_days_per_month=22
            ),
            PositionAttendanceRule(
                store_id=store2.id, position="店长", shift="常日班",
                start_time="09:00", end_time="18:00",
                base_salary=8500, full_attendance_bonus=500, allowance=1000,
                public_leave_days=8, work_days_per_month=22
            ),
        ]
        for rule in rules:
            db.add(rule)
        
        # 创建工资标准
        salary_standards = [
            SalaryStandard(
                store_id=store1.id, position="店长",
                base_salary=8000, full_attendance_bonus=500, allowance=1000,
                public_leave_days=8, standard_work_days=22,
                min_net_salary=7000, max_net_salary=15000
            ),
            SalaryStandard(
                store_id=store1.id, position="导购",
                base_salary=4000, full_attendance_bonus=300, allowance=500,
                public_leave_days=5, standard_work_days=22,
                min_net_salary=3500, max_net_salary=8000
            ),
        ]
        for standard in salary_standards:
            db.add(standard)
        
        # 创建两个测试员工
        employee1 = Employee(
            employee_id="E001", id_card="110101199001011234",
            name="张三", store_id=store1.id, position="店长",
            shift="常日班", base_salary=8000, hourly_rate=50,
            full_attendance_bonus=500, allowance=1000,
            public_leave_days=8, work_years=3, seniority_bonus=300,
            phone="13800138001", hire_date=date(2023, 1, 15),
            probation=False, status="在职"
        )
        employee2 = Employee(
            employee_id="E002", id_card="110101199205205678",
            name="李四", store_id=store1.id, position="导购",
            shift="常日班", base_salary=4000, hourly_rate=30,
            full_attendance_bonus=300, allowance=500,
            public_leave_days=5, work_years=1.5, seniority_bonus=150,
            phone="13800138002", hire_date=date(2023, 7, 1),
            probation=False, status="在职"
        )
        db.add(employee1)
        db.add(employee2)
        db.flush()
        
        # 生成最近一个月的考勤记录
        today = date.today()
        for i in range(30):
            work_date = today - timedelta(days=i)
            if work_date.weekday() < 5:  # 周一到周五
                for emp in [employee1, employee2]:
                    check_in = datetime.combine(work_date, datetime.strptime("08:55", "%H:%M").time())
                    check_out = datetime.combine(work_date, datetime.strptime("18:05", "%H:%M").time())
                    
                    # 随机添加一些迟到早退情况
                    if i == 5 and emp.id == employee2.id:
                        check_in = datetime.combine(work_date, datetime.strptime("09:35", "%H:%M").time())
                    if i == 10 and emp.id == employee1.id:
                        check_out = datetime.combine(work_date, datetime.strptime("17:20", "%H:%M").time())
                    
                    record = AttendanceRecord(
                        employee_id=emp.id, date=work_date,
                        check_in_time=check_in, check_out_time=check_out,
                        work_hours=8.0, overtime_hours=0.0, status="normal"
                    )
                    db.add(record)
        
        # 创建一个请假申请
        leave = LeaveRequest(
            employee_id=employee2.id, leave_type="事假",
            start_date=today - timedelta(days=20),
            end_date=today - timedelta(days=20),
            reason="家中有事", status="approved"
        )
        db.add(leave)
        
        # 创建上个月的工资记录
        last_month = today.replace(day=1) - timedelta(days=1)
        salary1 = SalaryRecord(
            employee_id=employee1.id, year=last_month.year, month=last_month.month,
            base_salary=8000, overtime_pay=0, bonus=500, deduction=0,
            commission=1000, late_deduction=0, absence_deduction=0,
            total_salary=9500, work_days=22, actual_work_days=22, leave_days=0
        )
        salary2 = SalaryRecord(
            employee_id=employee2.id, year=last_month.year, month=last_month.month,
            base_salary=4000, overtime_pay=200, bonus=300, deduction=100,
            commission=500, late_deduction=50, absence_deduction=0,
            total_salary=4850, work_days=22, actual_work_days=21, leave_days=1
        )
        db.add(salary1)
        db.add(salary2)
        
        db.commit()
        print("测试数据初始化完成！")
        print("\n测试数据概览:")
        print(f"- 店面: 2个 (朝阳门店、海淀门店)")
        print(f"- 员工: 2人 (张三-店长, 李四-导购)")
        print(f"- 考勤记录: 约30天")
        print(f"- 工资记录: 1个月")
        print("\n管理员账号:")
        print("- 用户名: admin")
        print("- 密码: test123")
        
    except Exception as e:
        db.rollback()
        print(f"初始化失败: {e}")
        raise
    finally:
        db.close()


def init_admin_user():
    """初始化管理员用户"""
    db = SessionLocal()
    try:
        from config import get_settings
        settings = get_settings()
        
        existing = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if not existing:
            admin = User(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                is_admin=True,
                is_active=True
            )
            db.add(admin)
            db.commit()
            print(f"管理员用户 {settings.ADMIN_USERNAME} 创建成功")
    finally:
        db.close()


def reset_database():
    """重置数据库"""
    print("警告: 这将删除所有现有数据！")
    confirm = input("确定要重置数据库吗？(yes/no): ")
    if confirm.lower() != 'yes':
        print("已取消")
        return
    
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("数据库已重置")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        reset_database()
    else:
        # 创建表结构
        Base.metadata.create_all(bind=engine)
        # 初始化管理员
        init_admin_user()
        # 初始化测试数据
        init_test_data()
