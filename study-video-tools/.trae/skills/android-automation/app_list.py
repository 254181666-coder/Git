#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取手机已安装App列表
"""

import uiautomator2 as u2
import json

def main():
    print("=" * 50)
    print("获取已安装App列表")
    print("=" * 50)
    
    # 连接设备
    try:
        d = u2.connect()
        print("✓ 设备连接成功\n")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return
    
    # 获取所有App
    apps = d.app_list()
    print(f"共找到 {len(apps)} 个App\n")
    
    # 分类显示
    common_apps = {
        "美团": "com.sankuai.meituan",
        "淘宝": "com.taobao.taobao",
        "京东": "com.jingdong.app.mall",
        "微信": "com.tencent.mm",
        "抖音": "com.ss.android.ugc.aweme",
        "支付宝": "com.eg.android.AlipayGphone",
        "微博": "com.sina.weibo",
        "B站": "tv.danmaku.bili",
        "小红书": "com.xingin.xhs",
    }
    
    print("常用App检查：")
    print("-" * 50)
    installed = []
    not_installed = []
    
    for name, package in common_apps.items():
        if package in apps:
            print(f"✓ {name:<10} {package}")
            installed.append((name, package))
        else:
            print(f"✗ {name:<10} {package}")
            not_installed.append((name, package))
    
    # 保存完整列表
    output = {
        "total": len(apps),
        "installed_common": installed,
        "not_installed_common": not_installed,
        "all_apps": apps
    }
    
    with open("app_list.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n" + "-" * 50)
    print(f"✓ 完整列表已保存到 app_list.json")
    print("\n你可以使用以下包名来启动App：")
    for name, package in installed:
        print(f"  d.app_start('{package}')  # {name}")

if __name__ == "__main__":
    main()
