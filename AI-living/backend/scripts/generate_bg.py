#!/usr/bin/env python3
"""生成测试用直播背景图"""
from PIL import Image, ImageDraw, ImageFont
import os

# 创建1080x1920竖屏背景
width, height = 1080, 1920
img = Image.new('RGB', (width, height), '#FF6B35')
draw = ImageDraw.Draw(img)

# 顶部标题栏
draw.rectangle([0, 0, width, 120], fill='#D63031')

# 中间产品展示区
draw.rectangle([50, 200, 1030, 800], fill='#FFFFFF')
draw.rectangle([50, 200, 1030, 800], outline='#FF6B35', width=5)

# 底部信息区
draw.rectangle([0, height-200, width, height], fill='#2D3436')

# 侧边装饰条
draw.rectangle([0, 120, 30, height-200], fill='#FFD700')
draw.rectangle([width-30, 120, width, height-200], fill='#FFD700')

# 装饰元素 - 圆形
draw.ellipse([800, 850, 1000, 1050], fill='#FFD700', outline='#FF6B35', width=5)
draw.ellipse([80, 850, 280, 1050], fill='#FFD700', outline='#FF6B35', width=5)

# 保存
os.makedirs('/Users/ann/Desktop/AI/Project/AI-living/backend/data', exist_ok=True)
filepath = '/Users/ann/Desktop/AI/Project/AI-living/backend/data/test_background.png'
img.save(filepath)
print(f'背景图已生成: {filepath}')
print(f'尺寸: {width}x{height}')
