#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import pymysql
import shutil
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG, SOURCE_DIR, ARCHIVE_DIR, LOGS_DIR, CATEGORY_MAP, PRODUCT_CATEGORY_MAP
from utils import simplify_store_name


def get_product_category(product_name):
    for key, category in PRODUCT_CATEGORY_MAP.items():
        if key in str(product_name):
            return category
    return '其他'


LOGS_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOGS_DIR / f"import_{datetime.now().strftime('%Y%m%d')}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)


def get_store_id(conn, store_name):
    clean = simplify_store_name(store_name)
    if not clean:
        return None
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM stores WHERE store_name = %s", (clean,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO stores (store_name) VALUES (%s)", (clean,))
    conn.commit()
    return cursor.lastrowid


def find_file(pattern):
    for f in SOURCE_DIR.iterdir():
        if not f.name.startswith('.') and pattern in f.name and f.suffix in ('.xlsx', '.xls', '.csv'):
            return f
    return None


def check_and_wait_for_files():
    """检测文件是否存在，如果不存在就等待文件到达"""
    log("检查数据文件...")
    
    # 需要等待的文件模式
    required_patterns = [
        '日营业数据*.xlsx',
        '会员储值订单*.xlsx',
        '商品销售汇总*.xlsx',
        '商品销售明细*.xlsx'
    ]
    
    # 最多等待时间（分钟）
    max_wait_minutes = 30
    check_interval_seconds = 60
    
    start_time = datetime.now()
    found_all_files = False
    
    while (datetime.now() - start_time).total_seconds() < max_wait_minutes * 60:
        # 检查是否有足够的文件
        has_files = False
        found_files = []
        
        for pattern in required_patterns:
            files = list(SOURCE_DIR.glob(pattern))
            if files:
                for f in files:
                    if '副本' not in f.name:
                        has_files = True
                        found_files.append(f.name)
                        break
        
        if has_files:
            log(f"  检测到文件: {', '.join(set(found_files))}")
            found_all_files = True
            break
        
        # 没有文件，等待
        waited = int((datetime.now() - start_time).total_seconds() / 60)
        remaining = max_wait_minutes - waited
        log(f"  未检测到数据文件，已等待 {waited} 分钟，还剩 {remaining} 分钟...")
        
        import time
        time.sleep(check_interval_seconds)
    
    if not found_all_files:
        log(f"  已等待 {max_wait_minutes} 分钟，仍未检测到完整数据文件，开始尝试导入现有文件...")
    
    return True


def check_already_imported_today():
    lock_file = LOGS_DIR / f".import_lock_{datetime.now().strftime('%Y%m%d')}"
    if lock_file.exists():
        with open(lock_file, 'r') as f:
            last_run = f.read().strip()
        log(f"今日数据已在 {last_run} 导入过，如需重新导入请先删除锁定文件")
        return True
    with open(lock_file, 'w') as f:
        f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    return False


def import_store_daily(conn):
    log("导入日营业数据...")
    f = find_file('日营业数据')
    if not f:
        log("  未找到日营业数据文件")
        return 0
    log(f"  文件: {f.name}")
    df = pd.read_excel(f)
    df.columns = [c.strip() for c in df.columns]
    cursor = conn.cursor()
    dates_to_delete = set()
    for _, row in df.iterrows():
        dv = row.get('日期')
        if not pd.isna(dv):
            dates_to_delete.add(str(dv)[:10])
    for ds in dates_to_delete:
        cursor.execute("DELETE FROM store_daily WHERE data_date = %s", (ds,))
    conn.commit()
    cols = [
        'store_id', 'data_date', 'weekday', 'total_revenue', 'actual_amount',
        'supermarket_revenue', 'room_revenue', 'stored_card_sales', 'times_card_sales',
        'other_revenue', 'transfer_fund', 'online_groupbuy', 'daily_batch_consumption',
        'customers_before_18', 'maintenance_before_18',
        'customers_18_to_24', 'maintenance_18_to_24',
        'customers_after_00', 'maintenance_after_00',
        'peak_room_count', 'peak_time', 'revenue', 'customers'
    ]
    placeholders = ','.join(['%s'] * len(cols))
    sql = f"INSERT INTO store_daily ({','.join(cols)}) VALUES ({placeholders})"
    count = 0
    for _, row in df.iterrows():
        store_name = simplify_store_name(row.get('门店', ''))
        if not store_name:
            continue
        date_val = row.get('日期')
        if pd.isna(date_val):
            continue
        try:
            store_id = get_store_id(conn, store_name)
            if not store_id:
                continue
            vals = [
                store_id, str(date_val)[:10],
                str(row.get('星期', '')),
                float(row.get('总计营业额', 0) or 0),
                float(row.get('实收金额', 0) or 0),
                float(row.get('超市收入', 0) or 0),
                float(row.get('房费收入', 0) or 0),
                float(row.get('储值卡销售', 0) or 0),
                float(row.get('次卡销售', 0) or 0),
                float(row.get('营业外', 0) or 0),
                float(row.get('往来资金', 0) or 0),
                float(row.get('线上团购应收', 0) or 0),
                float(row.get('日单批消费', 0) or 0),
                int(row.get('18点前待客', 0) or 0),
                int(row.get('18点前维护', 0) or 0),
                int(row.get('18点-24点待客', 0) or 0),
                int(row.get('18点-24点维护', 0) or 0),
                int(row.get('00点后待客', 0) or 0),
                int(row.get('00点后维护', 0) or 0),
                int(row.get('晚场待客最高峰台数', 0) or 0),
                str(row.get('晚场待客最高峰时点', '') or ''),
                float(row.get('总计营业额', 0) or 0),
                int(row.get('全天待客台数', 0) or 0)
            ]
            cursor.execute(sql, vals)
            count += 1
        except Exception:
            pass
    conn.commit()
    cursor.close()
    log(f"  导入 {count} 条记录")
    return count


def import_stored_value(conn):
    log("导入储值订单数据...")
    f = find_file('储值订单')
    if not f:
        log("  未找到储值订单文件")
        return 0
    log(f"  文件: {f.name}")

    match = re.search(r'(\d{4})_(\d{2})_(\d{2})', f.name)
    if match:
        file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        file_date = (datetime.strptime(file_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        file_date = None

    df = pd.read_excel(f)
    df.columns = [c.strip() for c in df.columns]
    cursor = conn.cursor()
    dates_to_del = set()
    for _, row in df.iterrows():
        dv = row.get('充值时间')
        if pd.notna(dv):
            try:
                dates_to_del.add(pd.to_datetime(dv).strftime('%Y-%m-%d'))
            except:
                pass
    for ds in dates_to_del:
        cursor.execute("DELETE FROM stored_value WHERE data_date = %s", (ds,))
    conn.commit()
    sv_cols = [
        'store_id', 'data_date', 'member_level', 'stored_amount', 'stored_count',
        'recharge_source', 'is_first_recharge', 'marketing_manager',
        'member_name', 'member_phone', 'room_principal', 'room_gift',
        'drink_principal', 'drink_gift', 'payment_method', 'payment_amount',
        'points_change', 'points_balance', 'growth_change', 'growth_balance',
        'total_balance', 'principal_balance', 'gift_balance', 'recharge_time'
    ]
    sv_ph = ','.join(['%s'] * len(sv_cols))
    sv_sql = f"INSERT INTO stored_value ({','.join(sv_cols)}) VALUES ({sv_ph})"
    count = 0
    for _, row in df.iterrows():
        if str(row.get('会员等级', '')).strip() == '合计':
            continue
        store_name = simplify_store_name(row.get('充值门店', ''))
        if not store_name:
            continue

        date_str = file_date
        time_str = ''
        date_val = row.get('充值时间')
        if pd.notna(date_val):
            try:
                time_str = pd.to_datetime(date_val).strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = str(date_val)

        store_id = get_store_id(conn, store_name)
        if not store_id:
            continue
        try:
            sv_vals = [
                store_id, date_str,
                str(row.get('会员等级', '')),
                float(row.get('酒水变动本金', 0) or 0), 1,
                str(row.get('充值来源', '')),
                1 if str(row.get('是否为首充', '否')) == '是' else 0,
                str(row.get('营销经理', '')),
                str(row.get('会员姓名', '')),
                str(row.get('会员电话', '')),
                float(row.get('房费变动本金', 0) or 0),
                float(row.get('房费变动赠金', 0) or 0),
                float(row.get('酒水变动本金', 0) or 0),
                float(row.get('酒水变动赠金', 0) or 0),
                str(row.get('支付方式', '')),
                float(row.get('支付金额', 0) or 0),
                int(row.get('变动积分', 0) or 0),
                int(row.get('积分余额', 0) or 0),
                int(row.get('变动成长值', 0) or 0),
                int(row.get('成长值余额', 0) or 0),
                float(row.get('合计余额', 0) or 0),
                float(row.get('本金余额', 0) or 0),
                float(row.get('赠送余额', 0) or 0),
                time_str
            ]
            cursor.execute(sv_sql, sv_vals)
            count += 1
        except Exception:
            pass
    conn.commit()
    cursor.close()
    log(f"  导入 {count} 条记录")
    return count


def import_product_sales(conn):
    log("导入商品销售数据...")
    detail_files = [f for f in SOURCE_DIR.glob("商品销售明细*.xlsx") if "副本" not in f.name]
    summary_files = [f for f in SOURCE_DIR.glob("商品销售汇总*.xlsx") if "副本" not in f.name]
    all_files = detail_files + summary_files
    
    if not all_files:
        log("  未找到商品销售文件")
        return 0
    
    cursor = conn.cursor()
    total_count = 0
    dates_to_delete = set()
    
    # 第一遍：收集所有日期，用于删除旧数据
    for f in sorted(all_files):
        try:
            df = pd.read_excel(f)
            df.columns = [c.strip() for c in df.columns]
            
            # 确定列名
            date_col = None
            if "销售日期::multi-filter" in df.columns:
                date_col = "销售日期::multi-filter"
            elif "销售日期" in df.columns:
                date_col = "销售日期"
            elif "日期" in df.columns:
                date_col = "日期"
            
            if not date_col:
                continue
            
            store_col = None
            if "门店名称" in df.columns:
                store_col = "门店名称"
            elif "门店" in df.columns:
                store_col = "门店"
            
            if not store_col:
                continue
            
            product_col = None
            if "商品名称" in df.columns:
                product_col = "商品名称"
            elif "商品名字" in df.columns:
                product_col = "商品名字"
            
            if not product_col:
                continue
            
            # 收集日期
            for idx, row in df.iterrows():
                try:
                    # 跳过合计行
                    if str(row.get(store_col, "")).strip() == "合计" or pd.isna(row.get(product_col, "")) or pd.isna(row.get(store_col, "")):
                        continue
                    
                    # 获取日期
                    date_val = row.get(date_col, None)
                    if pd.notna(date_val) and str(date_val).strip() != "":
                        try:
                            dt = pd.to_datetime(date_val)
                            dates_to_delete.add(dt.date())
                        except:
                            pass
                except:
                    pass
            
            # 如果文件里没有找到日期，尝试从文件名推断
            if not dates_to_delete:
                match = re.search(r"(\d{4})_(\d{2})_(\d{2})", f.name)
                if match:
                    file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    file_date_obj = datetime.strptime(file_date, "%Y-%m-%d").date()
                    data_date = file_date_obj - timedelta(days=1)
                    dates_to_delete.add(data_date)
        except Exception as e:
            pass
    
    # 删除旧数据
    if dates_to_delete:
        for d in dates_to_delete:
            cursor.execute("DELETE FROM product_sales WHERE data_date = %s", (d,))
        conn.commit()
        log(f"  已删除 {len(dates_to_delete)} 天的旧数据: {sorted(dates_to_delete)}")
    
    # 第二遍：正式导入
    for f in sorted(all_files):
        try:
            log(f"  文件: {f.name}")
            df = pd.read_excel(f)
            df.columns = [c.strip() for c in df.columns]
            
            # 确定列名
            date_col = None
            if "销售日期::multi-filter" in df.columns:
                date_col = "销售日期::multi-filter"
            elif "销售日期" in df.columns:
                date_col = "销售日期"
            elif "日期" in df.columns:
                date_col = "日期"
            
            if not date_col:
                continue
            
            store_col = None
            if "门店名称" in df.columns:
                store_col = "门店名称"
            elif "门店" in df.columns:
                store_col = "门店"
            
            if not store_col:
                continue
            
            product_col = None
            if "商品名称" in df.columns:
                product_col = "商品名称"
            elif "商品名字" in df.columns:
                product_col = "商品名字"
            
            if not product_col:
                continue
            
            # 确定其他列
            qty_col = "售卖数量" if "售卖数量" in df.columns else "总数量-小计"
            amount_col = "收入金额" if "收入金额" in df.columns else "销售金额-小计-折后"
            category_col = "套餐" if "套餐" in df.columns else "统计类别"
            room_col = "包厢类型::multi-filter" if "包厢类型::multi-filter" in df.columns else "包厢号" if "包厢号" in df.columns else "单位"
            system_category_col = "系统销售类别::multi-filter" if "系统销售类别::multi-filter" in df.columns else "系统销售类别"
            
            count = 0
            for idx, row in df.iterrows():
                try:
                    # 跳过合计行
                    if str(row.get(store_col, "")).strip() == "合计" or pd.isna(row.get(product_col, "")) or pd.isna(row.get(store_col, "")):
                        continue
                    
                    # 获取门店
                    store_id = get_store_id(conn, str(row.get(store_col, "")))
                    if not store_id:
                        continue
                    
                    # 获取日期
                    data_date = None
                    date_val = row.get(date_col, None)
                    if pd.notna(date_val) and str(date_val).strip() != "":
                        try:
                            dt = pd.to_datetime(date_val)
                            data_date = dt.date()
                        except:
                            pass
                    
                    # 如果没有找到日期，从文件名推断
                    if not data_date:
                        match = re.search(r"(\d{4})_(\d{2})_(\d{2})", f.name)
                        if match:
                            file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                            file_date_obj = datetime.strptime(file_date, "%Y-%m-%d").date()
                            data_date = file_date_obj - timedelta(days=1)
                    
                    if not data_date:
                        continue
                    
                    # 获取系统分类
                    system_cat = str(row.get(system_category_col, "其他")) if system_category_col in df.columns else "其他"
                    if system_cat in ["nan", "None", ""]:
                        system_cat = "其他"
                    big_category = CATEGORY_MAP.get(system_cat, "其他")
                    
                    # 插入数据
                    unit_price_val = float(row.get("单品售价", 0) if ("单品售价" in df.columns and pd.notna(row.get("单品售价"))) else 0)
                    cursor.execute("""
                        INSERT INTO product_sales
                        (store_id, data_date, product_name, category, unit_price, quantity, sales_amount, room_type, big_category)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        store_id,
                        data_date,
                        str(row.get(product_col, "")),
                        str(row.get(category_col, "")),
                        unit_price_val,
                        int(row.get(qty_col, 0) or 0),
                        float(row.get(amount_col, 0) or 0),
                        str(row.get(room_col, "")),
                        big_category
                    ))
                    count += 1
                except Exception as e:
                    pass
            
            total_count += count
            log(f"      导入 {count} 条")
        except Exception as e:
            log(f"  处理文件失败: {e}")
            pass
    
    conn.commit()
    cursor.close()
    log(f"  总计导入 {total_count} 条记录")
    return total_count


def import_product_sales_summary(conn):
    log("导入商品销售汇总表...")
    summary_files = [f for f in SOURCE_DIR.glob("商品销售汇总*.xlsx") if "副本" not in f.name]
    
    if not summary_files:
        log("  未找到商品销售汇总表文件")
        return 0
    
    total_count = 0
    for f in sorted(summary_files):
        log(f"  文件: {f.name}")
        try:
            df = pd.read_excel(f)
            df.columns = [c.strip() for c in df.columns]
            
            # 确定日期列
            date_col = None
            if "日期" in df.columns:
                date_col = "日期"
            elif "销售日期" in df.columns:
                date_col = "销售日期"
            elif "销售日期::multi-filter" in df.columns:
                date_col = "销售日期::multi-filter"
            
            # 收集所有日期，先删除旧数据
            all_dates = set()
            for _, row in df.iterrows():
                try:
                    if pd.isna(row.get("门店")) or str(row.get("门店")).strip() == "合计":
                        continue
                    
                    if date_col:
                        date_str = str(row.get(date_col, ""))
                        if "~" in date_str:
                            ds_part = date_str.split("~")[0]
                            if len(ds_part) == 8:
                                ds = f"{ds_part[:4]}-{ds_part[4:6]}-{ds_part[6:8]}"
                                all_dates.add(ds)
                        elif pd.notna(row.get(date_col)):
                            try:
                                dt = pd.to_datetime(row.get(date_col))
                                ds = dt.strftime("%Y-%m-%d")
                                all_dates.add(ds)
                            except:
                                pass
                except:
                    pass
            
            # 从文件名推断日期
            if not all_dates:
                match = re.search(r"(\d{4})_(\d{2})_(\d{2})", f.name)
                if match:
                    file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    file_date_obj = datetime.strptime(file_date, "%Y-%m-%d").date()
                    data_date = file_date_obj - timedelta(days=1)
                    all_dates.add(data_date.strftime("%Y-%m-%d"))
            
            # 删除旧数据
            cursor = conn.cursor()
            if all_dates:
                for ds in all_dates:
                    cursor.execute("DELETE FROM product_sales_summary WHERE data_date = %s", (ds,))
                conn.commit()
                log(f"  删除了旧数据: {sorted(all_dates)}")
            
            count = 0
            for _, row in df.iterrows():
                try:
                    # 跳过合计行
                    if pd.isna(row.get("门店")) or pd.isna(row.get("商品名字")):
                        continue
                    if str(row.get("门店")).strip() == "合计" or str(row.get("商品名字")).strip() == "合计":
                        continue
                    
                    # 获取门店ID
                    store_id = get_store_id(conn, str(row.get("门店", "")))
                    if not store_id:
                        continue
                    
                    # 获取日期
                    data_date = None
                    if date_col:
                        date_str = str(row.get(date_col, ""))
                        if "~" in date_str:
                            ds_part = date_str.split("~")[0]
                            if len(ds_part) == 8:
                                data_date = f"{ds_part[:4]}-{ds_part[4:6]}-{ds_part[6:8]}"
                        elif pd.notna(row.get(date_col)):
                            try:
                                dt = pd.to_datetime(row.get(date_col))
                                data_date = dt.strftime("%Y-%m-%d")
                            except:
                                pass
                    
                    # 从文件名推断日期
                    if not data_date:
                        match = re.search(r"(\d{4})_(\d{2})_(\d{2})", f.name)
                        if match:
                            file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                            file_date_obj = datetime.strptime(file_date, "%Y-%m-%d").date()
                            data_date = (file_date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
                    
                    if not data_date:
                        continue
                    
                    # 获取系统分类并映射big_category
                    system_category = str(row.get("系统销售类别::multi-filter", "其他"))
                    if system_category in ["nan", "None", ""]:
                        system_category = "其他"
                    big_category = CATEGORY_MAP.get(system_category, "其他")
                    
                    # 插入数据
                    cursor.execute("""
                        INSERT INTO product_sales_summary
                        (store_id, data_date, product_name, product_code, category, system_category, unit, unit_price, quantity, sales_amount, big_category)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        store_id,
                        data_date,
                        str(row.get("商品名字", "")),
                        str(row.get("商品编码", "")),
                        str(row.get("统计类别", "")),
                        system_category,
                        str(row.get("单位", "")),
                        float(row.get("单品售价", 0) or 0),
                        int(row.get("销售数量-小计", 0) or 0),
                        float(row.get("销售金额-小计-折后", 0) or 0),
                        big_category
                    ))
                    count += 1
                except Exception as e:
                    pass
            
            conn.commit()
            total_count += count
            log(f"      导入 {count} 条")
        except Exception as e:
            log(f"  处理文件失败: {e}")
            pass
    
    conn.commit()
    cursor.close()
    log(f"  总计导入 {total_count} 条记录")
    return total_count


def import_product_sales_detail(conn):
    log("导入商品销售明细表...")
    detail_files = [f for f in SOURCE_DIR.glob("商品销售明细*.xlsx") if "副本" not in f.name]
    
    if not detail_files:
        log("  未找到商品销售明细表文件")
        return 0
    
    total_count = 0
    for f in sorted(detail_files):
        log(f"  文件: {f.name}")
        try:
            df = pd.read_excel(f)
            df.columns = [c.strip() for c in df.columns]
            
            # 确定日期列
            date_col = None
            if "日期" in df.columns:
                date_col = "日期"
            elif "销售日期" in df.columns:
                date_col = "销售日期"
            elif "销售日期::multi-filter" in df.columns:
                date_col = "销售日期::multi-filter"
            
            # 收集所有日期，先删除旧数据
            all_dates = set()
            for _, row in df.iterrows():
                try:
                    if pd.isna(row.get("门店名称")) or str(row.get("门店名称")).strip() == "合计":
                        continue
                    
                    if date_col:
                        date_str = str(row.get(date_col, ""))
                        if pd.notna(row.get(date_col)):
                            try:
                                dt = pd.to_datetime(row.get(date_col))
                                ds = dt.strftime("%Y-%m-%d")
                                all_dates.add(ds)
                            except:
                                pass
                except:
                    pass
            
            # 从文件名推断日期
            if not all_dates:
                match = re.search(r"(\d{4})_(\d{2})_(\d{2})", f.name)
                if match:
                    file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    file_date_obj = datetime.strptime(file_date, "%Y-%m-%d").date()
                    data_date = file_date_obj - timedelta(days=1)
                    all_dates.add(data_date.strftime("%Y-%m-%d"))
            
            # 删除旧数据
            cursor = conn.cursor()
            if all_dates:
                for ds in all_dates:
                    cursor.execute("DELETE FROM product_sales_detail WHERE data_date = %s", (ds,))
                conn.commit()
                log(f"  删除了旧数据: {sorted(all_dates)}")
            
            count = 0
            for _, row in df.iterrows():
                try:
                    # 跳过合计行
                    if pd.isna(row.get("门店名称")) or pd.isna(row.get("商品名称")):
                        continue
                    if str(row.get("门店名称")).strip() == "合计" or str(row.get("商品名称")).strip() == "合计":
                        continue
                    
                    # 获取门店ID
                    store_id = get_store_id(conn, str(row.get("门店名称", "")))
                    if not store_id:
                        continue
                    
                    # 获取日期
                    data_date = None
                    if date_col:
                        date_str = str(row.get(date_col, ""))
                        if pd.notna(row.get(date_col)):
                            try:
                                dt = pd.to_datetime(row.get(date_col))
                                data_date = dt.strftime("%Y-%m-%d")
                            except:
                                pass
                    
                    # 从文件名推断日期
                    if not data_date:
                        match = re.search(r"(\d{4})_(\d{2})_(\d{2})", f.name)
                        if match:
                            file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                            file_date_obj = datetime.strptime(file_date, "%Y-%m-%d").date()
                            data_date = (file_date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
                    
                    if not data_date:
                        continue
                    
                    # 插入数据
                    cursor.execute("""
                        INSERT INTO product_sales_detail
                        (store_id, data_date, product_name, product_code, package, room_no, room_type, quantity, sales_amount, order_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        store_id,
                        data_date,
                        str(row.get("商品名称", "")),
                        str(row.get("商品编码", "")),
                        str(row.get("套餐", "")),
                        str(row.get("包厢号", "")),
                        str(row.get("包厢类型::multi-filter", "")),
                        int(row.get("售卖数量", 0) or 0),
                        float(row.get("收入金额", 0) or 0),
                        str(row.get("订单类型", "")),
                    ))
                    count += 1
                except Exception as e:
                    pass
            
            conn.commit()
            total_count += count
            log(f"      导入 {count} 条")
        except Exception as e:
            log(f"  处理文件失败: {e}")
            pass
    
    conn.commit()
    cursor.close()
    log(f"  总计导入 {total_count} 条记录")
    return total_count


def archive_source_files(processed_files):
    log("归档源数据文件...")
    today_str = datetime.now().strftime("%Y_%m_%d")
    archive_date_dir = ARCHIVE_DIR / f"source_{today_str}"
    archive_date_dir.mkdir(exist_ok=True, parents=True)
    moved_count = 0
    for f in processed_files:
        if f.exists():
            dest = archive_date_dir / f.name
            shutil.move(str(f), str(dest))
            log(f"  已归档: {f.name}")
            moved_count += 1
    log(f"  共归档 {moved_count} 个文件")
    return moved_count > 0


def map_time_period(tp):
    """把任意的time_period映射到ENUM允许的值"""
    if not tp:
        return '日场'
    tp = str(tp)
    if '午夜' in tp:
        return '午夜场'
    elif '黄金' in tp:
        return '黄金场'
    elif '晚' in tp:
        return '黄金场'
    else:
        return '日场'


def generate_order_daily():
    log("生成order_daily汇总表...")
    
    conn = get_conn()
    cursor = conn.cursor()
    
    # 获取 stores 表的映射
    cursor.execute("SELECT id, store_name FROM stores")
    store_map = {row[0]: row[1] for row in cursor.fetchall()}
    
    # 先清空 order_daily 表，然后重新生成
    cursor.execute("DELETE FROM order_daily")
    conn.commit()
    
    # 获取所有需要汇总的维度
    cursor.execute("""
        SELECT DISTINCT
            od.store_id,
            od.data_date,
            od.time_period,
            od.order_type,
            CASE WHEN od.source_channel LIKE '%团购%' THEN 1 ELSE 0 END as is_group_buy
        FROM order_detail od
        WHERE od.data_date IS NOT NULL
    """)
    
    rows = cursor.fetchall()
    total_inserted = 0
    
    for row in rows:
        store_id, data_date, time_period, order_type, is_group_buy = row
        
        store_name = store_map.get(store_id, '')
        if not store_name:
            store_name = '未知门店'
        
        # 映射time_period到允许的ENUM值
        mapped_time_period = map_time_period(time_period)
        
        # 计算统计信息 - 这里用原始time_period分组，但插入用映射后的值
        cursor.execute("""
            SELECT 
                COUNT(*) as item_count,
                SUM(actual_amount) as revenue
            FROM order_detail
            WHERE store_id = %s
                AND data_date = %s
                AND time_period = %s
                AND order_type = %s
                AND (source_channel LIKE '%%团购%%' OR %s = 0)
        """, (store_id, data_date, time_period, order_type, is_group_buy))
        
        item_count, revenue = cursor.fetchone()
        
        if item_count == 0:
            continue
        
        if revenue is None:
            revenue = 0
        
        try:
            cursor.execute("""
                INSERT INTO order_daily
                (data_date, store_name, store_name_raw, time_period, order_type, is_group_buy, item_count, revenue)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (data_date, store_name, store_name, mapped_time_period, order_type, is_group_buy, item_count, revenue))
            
            total_inserted += 1
        except Exception as e:
            # 忽略单个插入错误
            continue
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log(f"  order_daily表更新完成，共 {total_inserted} 条记录")


def main():
    if check_already_imported_today():
        return

    log("=" * 60)
    log("KTV 数据导入开始")
    log("=" * 60)
    
    # 等待文件到达
    check_and_wait_for_files()

    conn = get_conn()

    processed_files = []

    result_store = import_store_daily(conn)
    if result_store > 0:
        f = find_file('日营业数据')
        if f:
            processed_files.append(f)

    result_stored = import_stored_value(conn)
    if result_stored > 0:
        f = find_file('储值订单')
        if f:
            processed_files.append(f)

    result_product = import_product_sales(conn)
    if result_product > 0:
        for f in SOURCE_DIR.glob('商品销售明细*.xlsx'):
            if '副本' not in f.name and f.exists():
                processed_files.append(f)
        for f in SOURCE_DIR.glob('商品销售汇总*.xlsx'):
            if '副本' not in f.name and f.exists():
                processed_files.append(f)

    result_product_summary = import_product_sales_summary(conn)
    if result_product_summary > 0:
        for f in SOURCE_DIR.glob('商品销售汇总*.xlsx'):
            if '副本' not in f.name and f.exists():
                processed_files.append(f)
    
    result_product_detail = import_product_sales_detail(conn)
    if result_product_detail > 0:
        for f in SOURCE_DIR.glob('商品销售明细*.xlsx'):
            if '副本' not in f.name and f.exists():
                processed_files.append(f)

    conn.close()

    log("")
    log("=" * 60)
    log("导入结果")
    log("=" * 60)
    log(f"  日营业数据: {result_store} 条")
    log(f"  储值订单: {result_stored} 条")
    log(f"  商品销售数据: {result_product} 条")
    log(f"  商品销售汇总: {result_product_summary} 条")
    log(f"  商品销售明细: {result_product_detail} 条")

    archive_source_files(processed_files)
    
    # 生成order_daily汇总表
    generate_order_daily()

    log("=" * 60)
    log("数据导入完成")
    log("=" * 60)


if __name__ == "__main__":
    main()
