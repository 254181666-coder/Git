#!/usr/bin/env python3
import pymysql
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

conn = pymysql.connect(
    host='localhost', 
    port=3306, 
    user='root', 
    password='CHANGE_ME_MYSQL_PASSWORD', 
    database='ktv_analysis', 
    charset='utf8mb4'
)

print("=" * 100)
print("储值卡会员完整消耗分析 - 2026年1-2月")
print("=" * 100)

query_all_recharge = """
SELECT 
    s.store_name,
    sv.member_phone,
    sv.member_name,
    sv.member_level,
    sv.data_date as recharge_date,
    sv.stored_amount as recharge_principal,
    sv.payment_amount as payment_amount,
    sv.is_first_recharge,
    sv.total_balance as balance_after_recharge,
    sv.principal_balance as principal_after_recharge,
    sv.gift_balance as gift_after_recharge,
    sv.drink_principal,
    sv.room_principal,
    sv.marketing_manager
FROM stored_value sv
JOIN stores s ON sv.store_id = s.id
WHERE sv.data_date >= '2026-01-01' 
  AND sv.data_date <= '2026-02-28'
ORDER BY sv.data_date, s.store_name, sv.member_phone
"""

df_all_recharge = pd.read_sql(query_all_recharge, conn)

print(f"\n📊 1-2月储值总笔数: {len(df_all_recharge)} 笔")
print(f"📊 1-2月储值会员数: {df_all_recharge['member_phone'].nunique()} 人")
print(f"📊 1-2月储值总本金: ¥{df_all_recharge['recharge_principal'].sum():,.2f}")

df_first = df_all_recharge[df_all_recharge['is_first_recharge'] == 1]
df_repeat = df_all_recharge[df_all_recharge['is_first_recharge'] == 0]

print(f"\n   - 首充笔数: {len(df_first)} 笔 ({len(df_first)/len(df_all_recharge)*100:.1f}%)")
print(f"   - 复充笔数: {len(df_repeat)} 笔 ({len(df_repeat)/len(df_all_recharge)*100:.1f}%)")
print(f"   - 首充会员数: {df_first['member_phone'].nunique()} 人")
print(f"   - 复充会员数: {df_repeat['member_phone'].nunique()} 人")
print(f"   - 首充总金额: ¥{df_first['recharge_principal'].sum():,.2f}")
print(f"   - 复充总金额: ¥{df_repeat['recharge_principal'].sum():,.2f}")

query_all_members = """
SELECT 
    sv.store_id,
    s.store_name,
    sv.member_phone,
    sv.member_name,
    sv.member_level,
    MIN(sv.data_date) as first_recharge_date,
    MAX(sv.data_date) as last_recharge_date,
    SUM(sv.stored_amount) as total_recharge_principal,
    SUM(sv.payment_amount) as total_payment_amount,
    COUNT(*) as recharge_count,
    SUM(CASE WHEN sv.is_first_recharge = 1 THEN 1 ELSE 0 END) as first_recharge_count,
    SUM(CASE WHEN sv.is_first_recharge = 0 THEN 1 ELSE 0 END) as repeat_recharge_count,
    sv.marketing_manager
FROM stored_value sv
JOIN stores s ON sv.store_id = s.id
WHERE sv.data_date >= '2026-01-01' 
  AND sv.data_date <= '2026-02-28'
GROUP BY sv.store_id, s.store_name, sv.member_phone, sv.member_name, 
         sv.member_level, sv.marketing_manager
"""

df_all_members = pd.read_sql(query_all_members, conn)

phones = df_all_members['member_phone'].unique().tolist()
phone_list = [str(p) for p in phones if p and str(p) != 'nan' and str(p).strip()]

phones_str = ','.join([f"'{p}'" for p in phone_list])

query_balance = """
SELECT 
    mb.member_phone,
    mb.member_name,
    mb.change_store,
    mb.change_time as latest_change_time,
    mb.principal_balance,
    mb.gift_balance,
    mb.principal_change,
    mb.gift_change,
    mb.change_type
FROM member_balance_change mb
WHERE mb.change_time = (
    SELECT MAX(change_time) 
    FROM member_balance_change mb2 
    WHERE mb2.member_phone = mb.member_phone
)
AND mb.member_phone IN ({phones})
""".format(phones=phones_str)

df_latest_balance = pd.read_sql(query_balance, conn)
print(f"\n📊 能查到最新余额的1-2月会员数: {len(df_latest_balance)} 人")

query_consumption = """
SELECT 
    mb.member_phone,
    COUNT(*) as consumption_count,
    SUM(CASE WHEN mb.principal_change < 0 THEN mb.principal_change ELSE 0 END) as total_principal_consumed,
    SUM(CASE WHEN mb.gift_change < 0 THEN mb.gift_change ELSE 0 END) as total_gift_consumed,
    MIN(change_time) as first_consumption_time,
    MAX(change_time) as last_consumption_time
FROM member_balance_change mb
WHERE mb.member_phone IN ({phones})
AND mb.change_type IN ('消费扣款', '消费', '扣款')
AND (mb.principal_change < 0 OR mb.gift_change < 0)
GROUP BY mb.member_phone
""".format(phones=phones_str)

try:
    df_consumption = pd.read_sql(query_consumption, conn)
    print(f"📊 有消费记录的会员数: {len(df_consumption)} 人")
except:
    query_consumption2 = """
    SELECT 
        mb.member_phone,
        COUNT(*) as consumption_count,
        SUM(CASE WHEN mb.principal_change < 0 THEN mb.principal_change ELSE 0 END) as total_principal_consumed,
        SUM(CASE WHEN mb.gift_change < 0 THEN mb.gift_change ELSE 0 END) as total_gift_consumed,
        MIN(change_time) as first_consumption_time,
        MAX(change_time) as last_consumption_time
    FROM member_balance_change mb
    WHERE mb.member_phone IN ({phones})
    AND (mb.principal_change < 0 OR mb.gift_change < 0)
    GROUP BY mb.member_phone
    """.format(phones=phones_str)
    df_consumption = pd.read_sql(query_consumption2, conn)
    print(f"📊 有消耗记录的会员数: {len(df_consumption)} 人")

if not df_all_members.empty and not df_latest_balance.empty:
    df_final = df_all_members.merge(
        df_latest_balance[['member_phone', 'principal_balance', 'gift_balance', 'latest_change_time', 'change_store']], 
        on='member_phone', 
        how='left',
        suffixes=('_member', '_balance')
    )
    
    df_final['principal_consumed_calc'] = df_final['total_recharge_principal'] - df_final['principal_balance'].fillna(0)
    df_final['consumption_rate'] = (df_final['principal_consumed_calc'] / df_final['total_recharge_principal'] * 100).round(1)
    
    member_name_col = 'member_name_member' if 'member_name_member' in df_final.columns else 'member_name'
    if member_name_col not in df_final.columns:
        member_name_col = 'member_name'
    
    if not df_consumption.empty:
        df_final = df_final.merge(df_consumption, on='member_phone', how='left', suffixes=('', '_consumption'))
        df_final['consumption_count'] = df_final['consumption_count'].fillna(0).astype(int)
        df_final['total_principal_consumed'] = df_final['total_principal_consumed'].fillna(0)
        df_final['total_gift_consumed'] = df_final['total_gift_consumed'].fillna(0)
    
    print("\n" + "=" * 100)
    print("📈 汇总统计")
    print("=" * 100)
    
    if not df_final.empty:
        print(f"\n📊 1-2月储值会员总数: {len(df_final)} 人")
        print(f"📊 总充值本金: ¥{df_final['total_recharge_principal'].sum():,.2f}")
        print(f"📊 总剩余本金: ¥{df_final['principal_balance'].sum():,.2f}")
        print(f"📊 总消耗本金: ¥{df_final['principal_consumed_calc'].sum():,.2f}")
        print(f"📊 平均消耗比例: {df_final['consumption_rate'].mean():.1f}%")
        
        print(f"\n📊 充值频次分布:")
        recharge_dist = df_final['recharge_count'].value_counts().sort_index()
        for count, num_members in recharge_dist.items():
            pct = num_members / len(df_final) * 100
            print(f"   充值{count}次: {num_members}人 ({pct:.1f}%)")
        
        print(f"\n📊 复购率统计:")
        repeat_members = len(df_final[df_final['repeat_recharge_count'] > 0])
        first_members = len(df_final[df_final['first_recharge_count'] > 0])
        print(f"   首充会员: {first_members}人")
        print(f"   复充会员: {repeat_members}人")
        print(f"   复购率: {repeat_members/first_members*100:.1f}%")
        
        if 'consumption_count' in df_final.columns:
            print(f"\n📊 消耗频次统计:")
            print(f"   有消耗记录的会员: {df_final[df_final['consumption_count'] > 0].shape[0]}人")
            print(f"   无消耗记录的会员: {df_final[df_final['consumption_count'] == 0].shape[0]}人")
            print(f"   平均消耗次数: {df_final['consumption_count'].mean():.1f}次")
            print(f"   中位消耗次数: {df_final['consumption_count'].median():.1f}次")
            
            cons_dist = df_final[df_final['consumption_count'] > 0]['consumption_count'].describe()
            print(f"   最多消耗次数: {int(df_final['consumption_count'].max())}次")
            print(f"   最少消耗次数: {int(df_final[df_final['consumption_count'] > 0]['consumption_count'].min())}次")
        
        print("\n" + "=" * 100)
        print("🏪 各门店储值卡统计")
        print("=" * 100)
        
        store_summary = df_final.groupby('store_name').agg(
            会员数=('member_phone', 'nunique'),
            总充值本金=('total_recharge_principal', 'sum'),
            总剩余本金=('principal_balance', 'sum'),
            总消耗本金=('principal_consumed_calc', 'sum'),
            平均充值次数=('recharge_count', 'mean'),
            复购人数=('repeat_recharge_count', lambda x: (x > 0).sum()),
        ).reset_index().sort_values('总充值本金', ascending=False)
        
        store_summary['消耗比例'] = (store_summary['总消耗本金'] / store_summary['总充值本金'] * 100).round(1)
        store_summary['复购率'] = (store_summary['复购人数'] / store_summary['会员数'] * 100).round(1)
        
        print("\n{:<12} {:>6} {:>12} {:>12} {:>12} {:>8} {:>8} {:>8}".format(
            "门店", "会员数", "总充值本金", "总消耗本金", "总剩余本金", "消耗比例", "均充值次", "复购率"))
        print("-" * 95)
        for _, row in store_summary.iterrows():
            print("{:<12} {:>6} {:>12,.0f} {:>12,.0f} {:>12,.0f} {:>7.1f}% {:>7.1f} {:>7.1f}%".format(
                row['store_name'][:12],
                row['会员数'],
                row['总充值本金'],
                row['总消耗本金'],
                row['总剩余本金'],
                row['消耗比例'],
                row['平均充值次数'],
                row['复购率']
            ))
        
        print("\n" + "=" * 100)
        print("👥 会员明细 (前50条)")
        print("=" * 100)
        
        print("\n{:<12} {:<8} {:>6} {:>6} {:>10} {:>10} {:>10} {:>8} {:>8}".format(
            "门店", "会员", "手机号", "充值次", "总充值本金", "已消耗", "剩余本金", "消耗比例", "消费次"))
        print("-" * 100)
        
        for _, row in df_final.head(50).iterrows():
            phone_display = str(row['member_phone'])[-4:] if row['member_phone'] else ''
            principal_bal = row['principal_balance'] if pd.notna(row['principal_balance']) else 0
            rate = row['consumption_rate'] if pd.notna(row['consumption_rate']) else 0
            cons_count = row.get('consumption_count', 0)
            print("{:<12} {:<8} {:>6} {:>6} {:>10,.0f} {:>10,.0f} {:>10,.0f} {:>7.1f}% {:>8}".format(
                row['store_name'][:12],
                str(row[member_name_col])[:8],
                phone_display,
                int(row['recharge_count']),
                row['total_recharge_principal'],
                row['principal_consumed_calc'],
                principal_bal,
                rate,
                int(cons_count)
            ))
        
        print(f"\n... 共 {len(df_final)} 条记录")
        
        output_file = PROJECT_ROOT / "reports" / "jan_feb_stored_card_full_analysis.csv"
        output_file.parent.mkdir(exist_ok=True)
        df_final.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✅ 完整数据已保存到: {output_file}")

conn.close()

print("\n" + "=" * 100)
print("✅ 分析完成")
print("=" * 100)
