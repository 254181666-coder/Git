#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美团评论爬取示例
注意：请遵守美团用户协议，仅用于学习用途
"""

import uiautomator2 as u2
import time
import json
from datetime import datetime

class MeituanScraper:
    def __init__(self):
        self.d = None
        self.comments = []
        
    def connect(self):
        """连接设备"""
        print("连接设备...")
        try:
            self.d = u2.connect()
            print("✓ 设备连接成功")
            return True
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            return False
    
    def open_meituan(self):
        """打开美团"""
        print("\n打开美团...")
        try:
            self.d.app_start("com.sankuai.meituan")
            print("✓ 美团已启动")
            time.sleep(5)
            return True
        except Exception as e:
            print(f"✗ 启动失败: {e}")
            return False
    
    def extract_text_elements(self):
        """提取当前页面所有文本元素"""
        texts = []
        try:
            # 获取界面XML
            xml = self.d.dump_hierarchy()
            
            # 通过uiautomator2获取所有TextView
            elements = self.d(className="android.widget.TextView")
            for i, elem in enumerate(elements):
                try:
                    info = elem.info
                    text = info.get('text', '')
                    if text and len(text.strip()) > 2:  # 过滤短文本
                        texts.append({
                            'index': i,
                            'text': text,
                            'bounds': info.get('bounds', {}),
                            'visible': info.get('visibleBounds', {})
                        })
                except:
                    pass
        except Exception as e:
            print(f"提取文本时出错: {e}")
        
        return texts
    
    def scrape_comments(self, max_pages=3):
        """爬取评论"""
        print(f"\n开始爬取评论 (最多{max_pages}页)...")
        
        for page in range(max_pages):
            print(f"\n--- 第 {page + 1} 页 ---")
            
            # 提取当前页面文本
            texts = self.extract_text_elements()
            print(f"找到 {len(texts)} 个文本元素")
            
            # 筛选评论（根据特征）
            for item in texts:
                text = item['text']
                # 简单的评论识别规则（可以根据实际界面调整）
                if len(text) > 10 and not any(keyword in text for keyword in [
                    '美团', '订单', '支付', '登录', '设置', '我的'
                ]):
                    comment_data = {
                        'content': text,
                        'page': page + 1,
                        'timestamp': datetime.now().isoformat(),
                        'position': item['bounds']
                    }
                    self.comments.append(comment_data)
                    print(f"  ✓ {text[:30]}...")
            
            # 滑动翻页
            if page < max_pages - 1:
                print("滑动翻页...")
                self.d.swipe(0.5, 0.8, 0.5, 0.2, duration=0.5)
                time.sleep(2)
        
        print(f"\n✓ 爬取完成，共收集 {len(self.comments)} 条数据")
    
    def save_data(self, filename="meituan_data.json"):
        """保存数据"""
        print(f"\n保存数据到 {filename}...")
        data = {
            'scrape_time': datetime.now().isoformat(),
            'total_comments': len(self.comments),
            'comments': self.comments
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 数据已保存")
    
    def screenshot(self, filename="page.png"):
        """截图"""
        self.d.screenshot(filename)
        print(f"✓ 截图已保存为 {filename}")
    
    def run(self):
        """运行完整流程"""
        print("=" * 60)
        print("美团数据爬取工具")
        print("=" * 60)
        
        # 连接设备
        if not self.connect():
            return
        
        # 截图初始页面
        self.screenshot("start_page.png")
        
        # 打开美团（可选，如果需要手动操作可注释）
        # self.open_meituan()
        
        print("\n提示：")
        print("  1. 请手动在美团中找到要爬取的页面")
        print("  2. 准备好后按回车键继续...")
        input()
        
        # 开始爬取
        self.scrape_comments(max_pages=5)
        
        # 保存数据
        self.save_data()
        
        # 截图结束页面
        self.screenshot("end_page.png")
        
        print("\n" + "=" * 60)
        print("爬取完成！")
        print("=" * 60)

def main():
    scraper = MeituanScraper()
    scraper.run()

if __name__ == "__main__":
    main()
