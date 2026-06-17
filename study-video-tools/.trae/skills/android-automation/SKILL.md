---
name: "android-automation"
description: "自动连接Android手机，操作app，爬取界面数据。Invoke when user wants to control Android phone, automate app operations, or scrape data from mobile apps like Meituan."
---

# Android手机自动化Skill

## 描述

这个skill帮助你通过数据线连接Android手机，自动打开app，模拟用户操作（点击、滑动、输入），并爬取界面数据。

## 何时使用

- 用户需要连接Android手机进行自动化操作
- 用户想自动打开某个app（如美团、淘宝等）
- 用户需要爬取手机界面上的数据（如评论、商品信息）
- 用户需要编写手机自动化脚本

## 前置准备

### 1. 手机端设置
- 开启「开发者选项」（连续点击「版本号」7次）
- 开启「USB调试」
- 开启「USB安装」（部分机型需要）
- 用数据线连接手机到电脑

### 2. 电脑端环境
- 安装Python 3.8+
- 安装ADB工具
- 安装uiautomator2库

## 核心指令

### 第一步：检查设备连接
```bash
# 查看已连接设备
adb devices
```
预期输出应该显示设备序列号和device状态。

### 第二步：安装uiautomator2
```bash
pip install uiautomator2
python -m uiautomator2 init  # 初始化手机端
```

### 第三步：编写自动化脚本

#### 基础连接测试
```python
import uiautomator2 as u2

# 连接设备
d = u2.connect()  # 默认连接第一个设备
# 或 d = u2.connect('设备序列号')

print(d.info)  # 打印设备信息
```

#### 打开app并操作
```python
import uiautomator2 as u2
import time

d = u2.connect()

# 打开美团
d.app_start("com.sankuai.meituan")
time.sleep(3)

# 点击元素（通过text）
d(text="美食").click()
time.sleep(2)

# 滑动屏幕
d.swipe(0.5, 0.8, 0.5, 0.2)  # 向上滑动
```

#### 爬取数据示例（美团评论）
```python
import uiautomator2 as u2
import time
import json

def scrape_meituan_comments():
    d = u2.connect()
    
    # 打开美团
    d.app_start("com.sankuai.meituan")
    time.sleep(5)
    
    comments = []
    
    # 滚动并收集评论
    for page in range(5):  # 爬取5页
        # 获取当前页面所有文本
        xml = d.dump_hierarchy()
        
        # 这里可以解析XML提取评论
        # 或者通过文本定位提取
        review_elements = d(className="android.widget.TextView")
        
        for elem in review_elements:
            try:
                text = elem.info['text']
                if text and len(text) > 5:  # 过滤短文本
                    comments.append({
                        'content': text,
                        'page': page + 1
                    })
            except:
                pass
        
        # 滑动翻页
        d.swipe(0.5, 0.8, 0.5, 0.2, duration=0.5)
        time.sleep(2)
    
    # 保存数据
    with open('meituan_comments.json', 'w', encoding='utf-8') as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)
    
    print(f"已爬取 {len(comments)} 条评论")
    return comments
```

### 第四步：使用weditor查看界面元素
```bash
pip install weditor
python -m weditor
```
这会打开一个网页，可以实时查看手机界面的元素信息。

## 常用操作命令

| 操作 | 代码 |
|------|------|
| 连接设备 | `d = u2.connect()` |
| 打开app | `d.app_start("包名")` |
| 点击文本 | `d(text="文字").click()` |
| 点击坐标 | `d.click(x, y)` |
| 输入文本 | `d.set_text("内容")` |
| 滑动屏幕 | `d.swipe(x1, y1, x2, y2)` |
| 截图 | `d.screenshot("screenshot.png")` |
| 获取当前包名 | `d.app_current()` |
| 按返回键 | `d.press("back")` |
| 获取界面XML | `d.dump_hierarchy()` |

## 常见app包名

| App | 包名 |
|-----|------|
| 美团 | `com.sankuai.meituan` |
| 淘宝 | `com.taobao.taobao` |
| 京东 | `com.jingdong.app.mall` |
| 微信 | `com.tencent.mm` |
| 抖音 | `com.ss.android.ugc.aweme` |

## 安全提示

1. 不要在登录、支付等敏感页面使用自动化
2. 遵守app的用户协议，不要用于非法用途
3. 适当添加延时，避免操作过快被检测
4. 定期检查脚本，防止界面变化导致失效

## 示例文件

这个skill还提供了以下示例脚本：
- `basic_usage.py` - 基础使用示例
- `meituan_scraper.py` - 美团评论爬取
- `app_list.py` - 获取已安装app列表
