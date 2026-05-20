
#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

GROUP_BUY_DIR = Path("/Users/ann/Desktop/团购")
OUTPUT_DIR = Path("/Users/ann/Desktop/AI/Project/每日报告/data/output")
OUTPUT_DIR.mkdir(exist_ok=True)

def analyze_meituan(file_path):
    df = pd.read_excel(file_path)
    sales = df['商品信息'].value_counts().reset_index()
    sales.columns = ['产品名称', '销量']
    return sales

def analyze_douyin(file_path):
    df = pd.read_excel(file_path)
    sales = df.groupby('商品名称', as_index=False)['购买数量'].sum()
    sales.columns = ['产品名称', '销量']
    sales = sales.sort_values('销量', ascending=False).reset_index(drop=True)
    return sales

def main():
    print("=" * 80)
    print("团购数据分析 - 各店面销量TOP5产品")
    print("=" * 80)
    print()
    
    store_results = {}
    
    store_names = ['佳木斯', '安达', '晨宇', '松原一', '松原二', '榆树', '法库', '锡盟', '鸡西']
    
    for store_name in store_names:
        store_results[store_name] = {}
        
        meituan_file = GROUP_BUY_DIR / f"{store_name}美团.xlsx"
        douyin_file = GROUP_BUY_DIR / f"{store_name}抖音.xlsx"
        
        if meituan_file.exists():
            print(f"【{store_name} - 美团】")
            sales = analyze_meituan(meituan_file)
            store_results[store_name]['美团'] = sales
            print(f"  总订单数: {sales['销量'].sum()}")
            print(f"  商品种类数: {len(sales)}")
            print("  TOP5:")
            for idx, row in sales.head(5).iterrows():
                print(f"    {idx+1}. {row['产品名称']} - 销量: {row['销量']}")
            print()
        
        if douyin_file.exists():
            print(f"【{store_name} - 抖音】")
            sales = analyze_douyin(douyin_file)
            store_results[store_name]['抖音'] = sales
            print(f"  总销量: {sales['销量'].sum()}")
            print(f"  商品种类数: {len(sales)}")
            print("  TOP5:")
            for idx, row in sales.head(5).iterrows():
                print(f"    {idx+1}. {row['产品名称']} - 销量: {row['销量']}")
            print()
        
        print("-" * 60)
        print()
    
    report_lines = []
    report_lines.append("# 各店面团购销量TOP5产品分析报告\n")
    report_lines.append(f"生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append("\n---\n")
    
    for store_name in store_names:
        if '美团' not in store_results[store_name] and '抖音' not in store_results[store_name]:
            continue
        
        report_lines.append(f"## {store_name}\n")
        
        if '美团' in store_results[store_name]:
            report_lines.append("### 美团\n")
            top5 = store_results[store_name]['美团'].head(5)
            for idx, row in top5.iterrows():
                report_lines.append(f"{idx+1}. {row['产品名称']} - 销量: {row['销量']}\n")
            report_lines.append("\n")
        
        if '抖音' in store_results[store_name]:
            report_lines.append("### 抖音\n")
            top5 = store_results[store_name]['抖音'].head(5)
            for idx, row in top5.iterrows():
                report_lines.append(f"{idx+1}. {row['产品名称']} - 销量: {row['销量']}\n")
            report_lines.append("\n")
        
        report_lines.append("---\n\n")
    
    report_file = OUTPUT_DIR / "团购销量TOP5分析报告.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)
    print(f"✅ Markdown报告已保存至: {report_file}")
    
    excel_file = OUTPUT_DIR / "团购销量TOP5分析报告.xlsx"
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        for store_name in store_names:
            if '美团' in store_results[store_name]:
                store_results[store_name]['美团'].head(10).to_excel(
                    writer, sheet_name=f"{store_name}_美团", index=False
                )
            if '抖音' in store_results[store_name]:
                store_results[store_name]['抖音'].head(10).to_excel(
                    writer, sheet_name=f"{store_name}_抖音", index=False
                )
    
    print(f"✅ Excel报告已保存至: {excel_file}")
    print()
    print("分析完成！")

if __name__ == "__main__":
    main()

