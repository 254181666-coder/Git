#!/usr/bin/env python3
"""生成带透明通道的虚拟人物图片（模拟抠图后的人物）"""
from PIL import Image, ImageDraw
import os

# 创建300x500的人物图片（带透明通道）
width, height = 300, 500
img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 头部
draw.ellipse([100, 30, 200, 130], fill='#FFC0CB')  # 粉色头部

# 身体
draw.rectangle([80, 130, 220, 350], fill='#4169E1')  # 蓝色衣服

# 手臂
draw.rectangle([40, 150, 80, 280], fill='#4169E1')  # 左臂
draw.rectangle([220, 150, 260, 280], fill='#4169E1')  # 右臂

# 腿部
draw.rectangle([100, 350, 140, 480], fill='#2F4F4F')  # 左腿
draw.rectangle([160, 350, 200, 480], fill='#2F4F4F')  # 右腿

# 脸部特征
draw.ellipse([120, 60, 145, 85], fill='white')  # 左眼白
draw.ellipse([155, 60, 180, 85], fill='white')  # 右眼白
draw.ellipse([128, 68, 138, 78], fill='black')  # 左眼珠
draw.ellipse([163, 68, 173, 78], fill='black')  # 右眼珠
draw.arc([130, 85, 170, 105], 0, 180, fill='red', width=3)  # 嘴巴

# 保存
os.makedirs('/Users/ann/Desktop/AI/Project/AI-living/backend/data', exist_ok=True)
filepath = '/Users/ann/Desktop/AI/Project/AI-living/backend/data/virtual_character.png'
img.save(filepath)
print(f'虚拟人物已生成: {filepath}')
print(f'尺寸: {width}x{height}')
print(f'格式: RGBA (带透明通道)')
