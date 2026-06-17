
#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pymysql
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG


def get_week_ranges():
    """获取上一周和本周的日期范围"""
    today = datetime(2026, 5, 3)
    this_week_start = today - timedelta(days=today.weekday())
    this_week_end = this_week_start + timedelta(days=6)
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(days=1)
    return {
        "last_week": (last_week_start.date(), last_week_end.date()),
        "this_week": (this_week_start.date(), this_week_end.date())
    }


def get_hour_of_day(dt):
    """获取小时数"""
    if dt:
        return dt.hour
    return None


def is_member(customer_phone):
    """判断是否是会员（有手机号就算会员）"""
    return bool(customer_phone and customer_phone.strip())


def analyze_store_data(conn, store_id, store_name, week_start, week_end):
    """分析单个门店的数据"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    sql = """
    SELECT 
        od.*,
        s.store_name
    FROM order_detail od
    JOIN stores s ON od.store_id = s.id
    WHERE od.store_id = %s
    AND od.data_date BETWEEN %s AND %s
    ORDER BY od.open_time
    """
    cursor.execute(sql, (store_id, week_start, week_end))
    orders = cursor.fetchall()
    
    hour_stats = defaultdict(lambda: {
        "total_orders": 0,
        "member_orders": 0,
        "guest_orders": 0,
        "total_amount": 0.0
    })
    
    after_midnight_orders = []
    
    for order in orders:
        open_time = order['open_time']
        if not open_time:
            continue
        
        hour = get_hour_of_day(open_time)
        customer_phone = order['customer_phone']
        member = is_member(customer_phone)
        
        hour_stats[hour]["total_orders"] += 1
        if member:
            hour_stats[hour]["member_orders"] += 1
        else:
            hour_stats[hour]["guest_orders"] += 1
        hour_stats[hour]["total_amount"] += float(order['actual_amount'] or 0)
        
        if hour is not None and hour >= 0 and hour < 6:
            after_midnight_orders.append(order)
    
    cursor.close()
    return hour_stats, after_midnight_orders, orders


def print_hourly_stats(store_name, week_label, hour_stats):
    """打印小时统计"""
    print(f"\n{'='*80}")
    print(f"{store_name} - {week_label} 时段消费分布")
    print(f"{'='*80}")
    print(f"{'时段':<10} {'总订单数':<10} {'会员订单':<10} {'散客订单':<10} {'总金额':<12}")
    print("-" * 80)
    
    for hour in sorted(hour_stats.keys()):
        stats = hour_stats[hour]
        period = f"{hour:02d}:00-{hour+1:02d}:00"
        print(f"{period:<10} {stats['total_orders']:<10} {stats['member_orders']:<10} {stats['guest_orders']:<10} ¥{stats['total_amount']:<10.2f}")


def print_after_midnight_details(store_name, week_label, orders):
    """打印00点以后的详细订单"""
    print(f"\n{'='*80}")
    print(f"{store_name} - {week_label} 00:00-06:00 详细订单 ({len(orders)} 笔)")
    print(f"{'='*80}")
    if not orders:
        print("该时段无订单")
        return
    
    print(f"{'开房时间':<20} {'包厢号':<10} {'开房人':<12} {'手机号':<15} {'是否会员':<8} {'实收金额':<12}")
    print("-" * 80)
    total_amount = 0
    member_count = 0
    guest_count = 0
    
    for order in orders:
        open_time = order['open_time'].strftime("%Y-%m-%d %H:%M") if order['open_time'] else ""
        room_no = order['room_no'] or ""
        customer_name = order['customer_name'] or ""
        customer_phone = order['customer_phone'] or ""
        member = is_member(customer_phone)
        actual_amount = float(order['actual_amount'] or 0)
        
        print(f"{open_time:<20} {room_no:<10} {customer_name:<12} {customer_phone:<15} {'是' if member else '否':<8} ¥{actual_amount:<10.2f}")
        
        total_amount += actual_amount
        if member:
            member_count += 1
        else:
            guest_count += 1
    
    print("-" * 80)
    print(f"总计: {len(orders)} 笔订单, 会员 {member_count} 笔, 散客 {guest_count} 笔, 总金额 ¥{total_amount:.2f}")


def main():
    print("=" * 80)
    print("午夜场消费时段分析 - 检查00点后消费造假情况")
    print("=" * 80)
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    
    week_ranges = get_week_ranges()
    
    stores = [
        (1, "鸡西店"),
        (8, "安达店"),
        (11, "通化店")
    ]
    
    for store_id, store_name in stores:
        for week_label, (week_start, week_end) in week_ranges.items():
            week_label_text = "上一周" if week_label == "last_week" else "本周"
            print(f"\n\n分析 {store_name} {week_label_text} ({week_start} 至 {week_end})")
            
            hour_stats, after_midnight_orders, all_orders = analyze_store_data(
                conn, store_id, store_name, week_start, week_end
            )
            
            print_hourly_stats(store_name, week_label_text, hour_stats)
            print_after_midnight_details(store_name, week_label_text, after_midnight_orders)
    
    conn.close()
    print("\n" + "=" * 80)
    print("分析完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()

