# Android手机自动化 Skill

这是一个Trae技能，用于自动化操作Android手机，包括连接设备、打开App、模拟用户操作、爬取界面数据等。

## 快速开始

### 1. 手机设置
- 打开「设置」→「关于手机」
- 连续点击「版本号」7次，开启开发者模式
- 返回设置，找到「开发者选项」
- 开启「USB调试」和「USB安装」
- 用数据线连接手机到电脑

### 2. 电脑安装依赖
```bash
# 安装Python依赖
pip install -r requirements.txt

# 初始化uiautomator2（会在手机上安装服务）
python -m uiautomator2 init

# 检查设备连接
adb devices
```

### 3. 运行示例
```bash
# 查看设备信息和已安装App
python basic_usage.py

# 获取App列表
python app_list.py

# 爬取美团数据（需要手动导航到目标页面）
python meituan_scraper.py
```

### 4. 查看界面元素
```bash
# 启动weditor查看器
python -m weditor
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 技能核心文档 |
| `basic_usage.py` | 基础使用示例 |
| `meituan_scraper.py` | 美团数据爬取示例 |
| `app_list.py` | 获取已安装App列表 |
| `requirements.txt` | Python依赖 |
| `README.md` | 本文件 |

## 常用操作

```python
import uiautomator2 as u2

# 连接设备
d = u2.connect()

# 打开App
d.app_start("com.sankuai.meituan")  # 美团

# 点击元素
d(text="美食").click()

# 滑动屏幕
d.swipe(0.5, 0.8, 0.5, 0.2)  # 向上滑动

# 输入文本
d.set_text("搜索内容")

# 截图
d.screenshot("screen.png")

# 按返回键
d.press("back")
```

## 安全提示

1. 不要在登录、支付等敏感页面使用自动化
2. 遵守各App的用户协议
3. 适当添加延时，避免操作过快
4. 仅供学习和研究使用

## 常见问题

**Q: 设备连接失败？**
A: 检查USB线、USB调试开关，运行`adb devices`确认设备

**Q: 找不到元素？**
A: 使用`python -m weditor`查看界面元素信息

**Q: 操作太快被检测？**
A: 在操作间添加`time.sleep(1-2)`延时
