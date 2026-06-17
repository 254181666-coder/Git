#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Android手机自动化 - 基础使用示例
"""

import uiautomator2 as u2
import time
import sys

def check_connection():
    """检查设备连接"""
    print("=" * 50)
    print("检查设备连接...")
    print("=" * 50)
    
    try:
        d = u2.connect()
        print("✓ 设备连接成功！")
        print(f"  设备信息: {d.info}")
        print(f"  屏幕尺寸: {d.window_size()}")
        return d
    except Exception as e:
        print(f"✗ 设备连接失败: {e}")
        print("\n请检查：")
        print("  1. 手机已通过USB连接电脑")
        print("  2. 手机已开启USB调试")
        print("  3. 运行 'adb devices' 查看设备")
        return None

def basic_operations(d):
    """基础操作演示"""
    print("\n" + "=" * 50)
    print("基础操作演示")
    print("=" * 50)
    
    # 获取当前运行的app
    current_app = d.app_current()
    print(f"\n当前运行的App: {current_app}")
    
    # 按Home键
    print("\n按Home键...")
    d.press("home")
    time.sleep(2)
    
    # 截图
    print("截图保存为 screenshot.png...")
    d.screenshot("screenshot.png")
    print("✓ 截图已保存")

def open_app(d, package_name):
    """打开指定App"""
    print(f"\n打开App: {package_name}")
    try:
        d.app_start(package_name)
        print(f"✓ App已启动")
        time.sleep(3)
        return True
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        return False

def list_installed_apps(d):
    """列出已安装的App"""
    print("\n" + "=" * 50)
    print("已安装的App列表")
    print("=" * 50)
    
    apps = d.app_list()
    print(f"\n共找到 {len(apps)} 个App")
    print("\n部分常用App:")
    common_apps = [
        "com.sankuai.meituan",  # 美团
        "com.taobao.taobao",    # 淘宝
        "com.tencent.mm",       # 微信
        "com.ss.android.ugc.aweme",  # 抖音
    ]
    for app in common_apps:
        if app in apps:
            print(f"  ✓ {app}")
        else:
            print(f"  ✗ {app} (未安装)")

def main():
    print("Android手机自动化 - 基础示例")
    print("=" * 50)
    
    # 检查连接
    d = check_connection()
    if not d:
        return
    
    # 列出已安装App
    list_installed_apps(d)
    
    # 基础操作
    basic_operations(d)
    
    print("\n" + "=" * 50)
    print("基础示例完成！")
    print("=" * 50)
    print("\n你可以：")
    print("  1. 修改此脚本添加更多操作")
    print("  2. 运行 'python -m weditor' 查看界面元素")
    print("  3. 查看 meituan_scraper.py 进行数据爬取")

if __name__ == "__main__":
    main()
