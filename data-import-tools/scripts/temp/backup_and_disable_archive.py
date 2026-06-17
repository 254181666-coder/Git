#!/usr/bin/env python3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
print("=" * 80)
print("备份并禁用 daily_archive 相关的脚本")
print("=" * 80)

# 备份目标目录
BACKUP_DIR = PROJECT_ROOT / "data" / "archive" / "backup_archive_scripts"
BACKUP_DIR.mkdir(exist_ok=True)

# 需要备份和禁用的文件
files_to_backup = [
    PROJECT_ROOT / "com.ktv.dailyarchive.plist",
    PROJECT_ROOT / "scripts" / "daily_archive.py",
    PROJECT_ROOT / "scripts" / "daily_archive.sh",
]

print("\n正在备份:")
for f in files_to_backup:
    if f.exists():
        dest = BACKUP_DIR / f.name
        dest.write_bytes(f.read_bytes())
        print(f"  ✅ {f.name} -> {BACKUP_DIR.name}")
    else:
        print(f"  ⚠️ {f.name} (不存在)")

print("\n正在禁用:")
# 重命名文件加 .disabled
for f in files_to_backup:
    if f.exists():
        disabled_name = f.parent / (f.name + ".disabled")
        if not disabled_name.exists():
            f.rename(disabled_name)
            print(f"  ✅ {f.name} -> {disabled_name.name}")
        else:
            print(f"  ⚠️ {disabled_name.name} 已存在")

print("\n" + "=" * 80)
print("确认状态:")
print("=" * 80)

# 确认文件状态
for f in files_to_backup:
    print(f"\n{f.name}:")
    if f.exists():
        print(f"  ⚠️  还在原位置！")
    else:
        disabled = f.parent / (f.name + ".disabled")
        if disabled.exists():
            print(f"  ✅ 已禁用: {disabled.name}")
        backup = BACKUP_DIR / f.name
        if backup.exists():
            print(f"  ✅ 已备份: {backup.name}")

print("\n" + "=" * 80)
print("✅ 完成！")
print("=" * 80)
