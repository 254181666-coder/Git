
#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
from src.database import query

GROUP_BUY_DIR = Path("/Users/ann/Desktop/团购")
OUTPUT_DIR = PROJECT_ROOT / "data/output"

STORE_NAME_MERGE = {
    '上东': '上东', '上东店': '上东',
    '临河街': None, '临河街店': None,
    '总部': None, '总部店': None,
    '晨宇': '晨宇', '晨宇店': '晨宇',
    '通辽': '通辽', '通辽店': '通辽',
    '松原一': '松原一', '松原一店': '松原一',
    '松原二': '松原二', '松原二店': '松原二',
    '佳木斯': '佳木斯', '佳木斯店': '佳木斯',
    '鸡西': '鸡西', '鸡西店': '鸡西',
    '红旗街': '红旗街', '红旗街店': '红旗街',
    '安达': '安达', '安达店': '安达',
    '榆树': '榆树', '榆树店': '榆树',
    '法库': '法库', '法库店': '法库',
    '通化': '通化', '通化店': '通化',
}

GB_SOURCES = {'抖音', '美团大众', '线下团购'}

def unify(n):
    if not n:
        return None
    return STORE_NAME_MERGE.get(str(n).strip(), str(n).strip())

def store_map():
    df = query("SELECT id, store_name FROM stores")
    return dict(zip(df['id'], df['store_name']))

def load_last_year_data():
    print("⏳ 加载去年(2025年5月)数据...")
    store_data = {}
    
    for store in ['佳木斯', '安达', '晨宇', '松原一', '松原二', '榆树', '法库', '锡盟', '鸡西']:
        store_data[store] = {'美团': None, '抖音': None}
        
        for platform in ['美团', '抖音']:
            file_path = GROUP_BUY_DIR / f"{store}{platform}.xlsx"
            if not file_path.exists():
                continue
            
            try:
                df = pd.read_excel(file_path)
                
                if platform == '美团':
                    if '消费时间' in df.columns:
                        df['data_date'] = pd.to_datetime(df['消费时间']).dt.date
                        df = df[(df['data_date'] >= date(2025, 5, 1)) & (df['data_date'] <= date(2025, 5, 11))]
                    store_data[store]['美团'] = df
                else:
                    if '下单时间' in df.columns:
                        df['data_date'] = pd.to_datetime(df['下单时间']).dt.date
                        df = df[(df['data_date'] >= date(2025, 5, 1)) & (df['data_date'] <= date(2025, 5, 11))]
                    store_data[store]['抖音'] = df
            except Exception as e:
                print(f"  ⚠️ {store}{platform} 读取失败: {e}")
    
    return store_data

def analyze_last_year(store_data):
    results = {}
    
    for store in store_data:
        results[store] = {
            '美团订单': 0, '美团营收': 0,
            '抖音订单': 0, '抖音营收': 0,
            '总订单': 0, '总营收': 0,
            '团购订单': 0, '热门套餐': []
        }
        
        meituan = store_data[store]['美团']
        douyin = store_data[store]['抖音']
        
        def clean_amount(s):
            if pd.isna(s):
                return 0.0
            s = str(s).strip()
            s = s.replace('¥', '').replace('元', '').replace(',', '')
            try:
                return float(s)
            except:
                return 0.0
        
        if meituan is not None and not meituan.empty:
            results[store]['美团订单'] = len(meituan)
            if '消费金额' in meituan.columns:
                results[store]['美团营收'] = float(meituan['消费金额'].apply(clean_amount).sum())
            elif '实际支付' in meituan.columns:
                results[store]['美团营收'] = float(meituan['实际支付'].apply(clean_amount).sum())
            else:
                results[store]['美团营收'] = 0.0
            
            if '商品信息' in meituan.columns:
                pkg_counts = meituan['商品信息'].value_counts().head(5)
                results[store]['热门套餐'].extend([f"{k}: {v}单" for k, v in pkg_counts.items()])
        
        if douyin is not None and not douyin.empty:
            results[store]['抖音订单'] = len(douyin)
            if '券用户实付金额' in douyin.columns:
                results[store]['抖音营收'] = float(douyin['券用户实付金额'].apply(clean_amount).sum())
            elif '用户实付金额' in douyin.columns:
                results[store]['抖音营收'] = float(douyin['用户实付金额'].apply(clean_amount).sum())
            else:
                results[store]['抖音营收'] = 0.0
            
            if '商品名称' in douyin.columns:
                pkg_counts = douyin['商品名称'].value_counts().head(5)
                results[store]['热门套餐'].extend([f"{k}: {v}单" for k, v in pkg_counts.items()])
        
        results[store]['总订单'] = results[store]['美团订单'] + results[store]['抖音订单']
        results[store]['总营收'] = float(results[store]['美团营收']) + float(results[store]['抖音营收'])
        results[store]['团购订单'] = results[store]['总订单']
    
    return results

last_year_data = load_last_year_data()
last_year_data = analyze_last_year(last_year_data)
print("检查去年数据结构:")
for s in last_year_data:
    print(f"  {s}: {list(last_year_data[s].keys())}")
