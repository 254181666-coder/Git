#!/usr/bin/env python3
import pandas as pd
import os
from pathlib import Path

GROUP_BUY_DIR = Path("/Users/ann/Desktop/团购")
OUTPUT_DIR = Path("/Users/ann/Desktop/AI/Project/每日报告/data/output")
OUTPUT_DIR.mkdir(exist_ok=True)

def analyze_file(file_path, store_name, platform):
    try:
        df = pd.read_excel(file_path)
        print(f"  文件: {file_path.name}")
        print(f"  列名: {list(df.columns)}")
        print(f"  总行数: {len(df)}")
        
        sales_col = None
        product_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if '销量' in col_lower or '销售' in col_lower or '量' in col_lower:
                sales_col = col
            if '商品' in col_lower or '产品' in col_lower or '名称' in col_lower:
                product_col = col
        
        if not sales_col:
            for col in df.columns:
                try:
                    pd.to_numeric(df[col], errors='raise')
                    sales_col = col
                    break
                except:
                    continue
        
        if not product_col:
            for col in df.columns:
                if df[col].dtype == 'object' and len(df[col].unique()) > 10:
                    product_col = col
                    break
        
        if not sales_col or not product_col:
            print(f"  ⚠️ 无法找到销量列或产品列")
            print(f"  销量列候选: {sales_col}")
            print(f"  产品列候选: {product_col}")
            return None
        
        print(f"  使用产品列: {product_col}")
        print(f"  使用销量列: {sales_col}")
        
        df_clean = df.copy()
        df_clean[sales_col] = pd.to_numeric(df_clean[sales_col], errors='coerce').fillna(0)
        df_clean = df_clean[df_clean[sales_col] > 0]
        
        df_grouped = df_clean.groupby(product_col)[sales_col].sum().reset_index()
        df_grouped = df_grouped.sort_values(sales_col, ascending=False)
        
        df_grouped.columns = ['产品名称', '销量']
        
        return df_grouped
        
    except Exception as e:
        print(f"  ❌ 处理失败: {e}")
        return None

def main():
    print("=" * 80)
    print("团购数据分析 - 各店面销量TOP5产品")
    print("=" * 80)
    print()
    
    store_results = {}
    
    files = sorted(GROUP_BUY_DIR.glob("*.xlsx"))
    
    for file_path in files:
        filename = file_path.name
        print(f"处理: {filename}")
        
        store_name = None
        platform = None
        
        for store in ['佳木斯', '安达', '晨宇', '松原一', '松原二', '榆树', '法库', '锡盟', '鸡西']:
            if store in filename:
                store_name = store
                break
        
        if '美团' in filename:
            platform = '美团'
        elif '抖音' in filename:
            platform = '抖音'
        
        if not store_name or not platform:
            print(f"  ⚠️ 无法识别店面或平台")
            print()
            continue
        
        if store_name not in store_results:
            store_results[store_name] = {}
        
        result_df = analyze_file(file_path, store_name, platform)
        
        if result_df is not None:
            store_results[store_name][platform] = result_df
            print(f"  ✅ 成功处理")
        
        print()
    
    print("=" * 80)
    print("分析结果汇总")
    print("=" * 80)
    print()
    
    report_lines = []
    report_lines.append("# 各店面团购销量TOP5产品分析报告\n")
    report_lines.append(f"生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append("\n---\n")
    
    for store_name in sorted(store_results.keys()):
        print(f"【{store_name}】")
        report_lines.append(f"## {store_name}\n")
        
        platforms = store_results[store_name]
        
        if '美团' in platforms:
            print("  美团TOP5:")
            report_lines.append("### 美团\n")
            top5_meituan = platforms['美团'].head(5)
            for idx, row in top5_meituan.iterrows():
                print(f"    {idx+1}. {row['产品名称']} - {row['销量']}")
                report_lines.append(f"{idx+1}. {row['产品名称']} - 销量: {row['销量']}\n")
            print()
        
        if '抖音' in platforms:
            print("  抖音TOP5:")
            report_lines.append("\n### 抖音\n")
            top5_douyin = platforms['抖音'].head(5)
            for idx, row in top5_douyin.iterrows():
                print(f"    {idx+1}. {row['产品名称']} - {row['销量']}")
                report_lines.append(f"{idx+1}. {row['产品名称']} - 销量: {row['销量']}\n")
            print()
        
        report_lines.append("\n---\n")
        print("-" * 60)
        print()
    
    report_file = OUTPUT_DIR / "团购销量TOP5分析报告.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)
    
    print(f"✅ 分析报告已保存至: {report_file}")
    
    excel_report = OUTPUT_DIR / "团购销量TOP5分析报告.xlsx"
    with pd.ExcelWriter(excel_report, engine='openpyxl') as writer:
        for store_name in sorted(store_results.keys()):
            platforms = store_results[store_name]
            if '美团' in platforms:
                platforms['美团'].head(10).to_excel(writer, sheet_name=f"{store_name}_美团", index=False)
            if '抖音' in platforms:
                platforms['抖音'].head(10).to_excel(writer, sheet_name=f"{store_name}_抖音", index=False)
    
    print(f"✅ Excel报告已保存至: {excel_report}")

if __name__ == "__main__":
    main()
