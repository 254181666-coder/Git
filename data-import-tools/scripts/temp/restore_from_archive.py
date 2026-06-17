
#!/usr/bin/env python3
"""
从 archive 目录恢复完整数据
1. 从 archive 目录复制所有需要的文件到 source 目录
2. 运行完整的导入脚本
"""
import sys
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置
ARCHIVE_ROOT = PROJECT_ROOT / 'data' / 'archive'
SOURCE_DIR = PROJECT_ROOT / 'data' / 'source'
LOGS_DIR = PROJECT_ROOT / 'data' / 'logs'

# 我们需要恢复的日期
TARGET_DATES = ['2026_04_24', '2026_04_25', '2026_04_26', '2026_04_27', '2026_04_28', '2026_04_29']

def clean_source_dir():
    """清空 source 目录"""
    print("清空 source 目录...")
    for f in SOURCE_DIR.iterdir():
        if f.name != '25nian.xlsx' and not f.name.startswith('.'):
            f.unlink()
            print(f"  删除: {f.name}")

def copy_from_archive():
    """从 archive 复制文件"""
    print("\n从 archive 复制文件到 source 目录...")
    copied = 0
    
    for date_str in TARGET_DATES:
        archive_dir = ARCHIVE_ROOT / f'source_{date_str}'
        if not archive_dir.exists():
            print(f"  跳过: {date_str} (目录不存在)")
            continue
        
        print(f"  处理: {date_str}")
        
        for f in archive_dir.iterdir():
            if f.name.startswith('.'):
                continue
            
            dest = SOURCE_DIR / f.name
            if not dest.exists():
                shutil.copy2(f, dest)
                print(f"    复制: {f.name}")
                copied += 1
    
    print(f"\n共复制 {copied} 个文件")
    return copied > 0

def remove_import_locks():
    """删除导入锁定文件，强制重新导入"""
    print("\n删除导入锁定文件...")
    for lock_file in LOGS_DIR.glob('.import_lock_*'):
        lock_file.unlink()
        print(f"  删除: {lock_file.name}")

def run_import():
    """运行导入脚本"""
    print("\n运行导入脚本...")
    
    # 导入相关模块
    from scripts.daily_import_with_archive import main as import_main
    
    try:
        import_main()
        print("\n✅ 导入完成！")
        return True
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        return False

def main():
    print("=" * 60)
    print("从 archive 恢复完整数据")
    print("=" * 60)
    
    # 1. 清空 source 目录
    clean_source_dir()
    
    # 2. 从 archive 复制文件
    if not copy_from_archive():
        print("\n❌ 没有文件可复制，退出")
        return
    
    # 3. 删除锁定文件
    remove_import_locks()
    
    # 4. 运行导入
    success = run_import()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 数据恢复完成！")
    else:
        print("❌ 数据恢复失败！")
    print("=" * 60)


if __name__ == "__main__":
    main()
