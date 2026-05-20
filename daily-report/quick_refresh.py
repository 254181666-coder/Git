#!/usr/bin/env python3
"""
一键刷新报表脚本
快速手动触发：生成报表 + 复制到交付目录
使用方法：
    python3 quick_refresh.py              # 刷新昨天的报表
    python3 quick_refresh.py 2026-04-29   # 刷新指定日期的报表
"""
import sys
import os
from pathlib import Path
from datetime import date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_header(text):
    """打印标题"""
    print("=" * 60)
    print(f"📊 {text}")
    print("=" * 60)


def generate_charts(target_date):
    """生成轻舟日报图表"""
    print_header("第1步：生成轻舟日报图表")
    
    try:
        from scripts.generate_qingzhou_charts import main as generate_charts
        sys.argv = ['generate_qingzhou_charts.py', target_date]
        generate_charts()
        print("   ✅ 图表生成完成")
        return True
    except Exception as e:
        print(f"   ❌ 图表生成失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def generate_product_report(target_date):
    """生成商品销售报告"""
    print_header("第2步：生成商品销售报告")
    
    try:
        from scripts.generate_product_sales_report import generate_html_report
        generate_html_report(target_date)
        print("   ✅ 商品销售报告生成完成")
        return True
    except Exception as e:
        print(f"   ❌ 商品销售报告生成失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def generate_yearly_comparison_report(target_date):
    """生成同比对比报告"""
    print_header("第3步：生成同比对比报告")

    try:
        from scripts.generate_yearly_comparison_report import main as generate_report
        sys.argv = ['generate_yearly_comparison_report.py', target_date]
        generate_report()
        print("   ✅ 同比对比报告生成完成")
        return True
    except Exception as e:
        print(f"   ❌ 同比对比报告生成失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def clear_extended_attributes(file_path: Path):
    """清除文件的扩展属性，避免访问权限问题"""
    import subprocess
    try:
        subprocess.run(['xattr', '-c', str(file_path)], capture_output=True, check=True)
    except:
        pass


def copy_to_delivery(target_date):
    """复制到交付目录"""
    print_header("第4步：复制到交付目录")
    
    try:
        import shutil
        OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
        OUTPUT_PDF_DIR = PROJECT_ROOT / "data" / "output_pdf"
        from src.config import DELIVERY_DIR
        DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
        
        files = [
            OUTPUT_DIR / f"{target_date}储值率分析图.png",
            OUTPUT_DIR / f"收入分析综合图_{target_date}.png",
            OUTPUT_PDF_DIR / f"商品销售分析报告_{target_date}.pdf",
            OUTPUT_PDF_DIR / f"同比对比分析报告_{target_date}.pdf",
        ]
        
        for src in files:
            if src.exists():
                dest = DELIVERY_DIR / src.name
                shutil.copy2(str(src), str(dest))
                clear_extended_attributes(dest)
                print(f"   ✓ {src.name}")
            else:
                print(f"   ⚠️ 文件不存在: {src.name}")
        
        print("   ✅ 已复制到交付目录")
        return True
    except Exception as e:
        print(f"   ❌ 复制失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    # 确定目标日期
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print_header(f"一键刷新报表 - {target_date}")
    
    # 回到每日报告项目目录
    os.chdir(str(PROJECT_ROOT))
    
    success = True
    
    # 1. 生成图表
    success = generate_charts(target_date) and success
    
    # 2. 生成商品销售报告
    success = generate_product_report(target_date) and success

    # 3. 生成同比对比报告
    success = generate_yearly_comparison_report(target_date) and success

    # 4. 复制到交付目录
    success = copy_to_delivery(target_date) and success
    
    print_header("完成")
    if success:
        print("✅ 所有任务完成！")
        print(f"📂 输出目录：{PROJECT_ROOT / 'data' / 'output'}")
        from src.config import DELIVERY_DIR
        print(f"📂 交付目录：{DELIVERY_DIR}")
    else:
        print("❌ 部分任务失败，请检查上面的日志")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
