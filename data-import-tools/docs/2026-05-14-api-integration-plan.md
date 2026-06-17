# 数据导入项目 - OpenAPI对接改造实施计划

> **For agentic workers:** Use subagent-driven-development to implement this plan. Steps use checkbox syntax for tracking.

**Goal:** 将数据导入项目数据源从"影刀下载Excel文件"改为"业务系统OpenAPI拉取"，解决影刀不稳定问题，同时保留现有数据库架构，每日报表和Manpower看板无需改动。

**Architecture:**
- 新增API客户端模块，处理认证、请求、重试
- 新增每日API拉取脚本，替换原文件检测逻辑
- 数据解析从Excel读取改为JSON解析
- 保持原有的数据库写入逻辑不变（表结构不变，报表/看板无需改动）
- 新增失败通知机制，拉取/导入失败发送飞书通知

**Tech Stack:**
- Python 3.x
- requests 库发送HTTP请求
- pymysql 数据库操作（已有）
- pandas 数据处理（已有）
- 飞书机器人webhook 发送通知

---

## Task 1: 新增API配置模块

**Files:**
- Create: `api_client.py` (根目录)
- Modify: `config.py` (根目录)

- [ ] **Step 1: 在config.py中新增API配置**

```python
# ========== 业务系统OpenAPI配置 ==========
API_BASE_URL = "https://api.example.com"  # 替换为实际地址
API_APP_KEY = "your-app-key"              # 替换为实际app key
API_APP_SECRET = "your-app-secret"        # 替换为实际secret
# 飞书通知配置（失败通知）
FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
```

- [ ] **Step 2: 创建api_client.py基础框架**

```python
"""
业务系统OpenAPI客户端
处理认证、请求、重试
"""
import time
import requests
from datetime import datetime, timedelta
from config import API_BASE_URL, API_APP_KEY, API_APP_SECRET

class BusinessAPIClient:
    def __init__(self):
        self.access_token = None
        self.token_expire_time = 0
    
    def get_access_token(self):
        """获取/刷新access_token"""
        # 根据实际API认证方式实现
        pass
    
    def request(self, method, endpoint, params=None, json_body=None, retry=3):
        """发送请求，自动重试"""
        pass
    
    def get_daily_business_data(self, date: datetime):
        """获取指定日期的营业数据"""
        pass
    
    def get_member_recharge_data(self, date: datetime):
        """获取指定日期的会员储值数据"""
        pass
    
    def get_product_sales_data(self, date: datetime):
        """获取指定日期的商品销售数据"""
        pass
    
    def get_order_detail_data(self, date: datetime):
        """获取指定日期的订单明细数据"""
        pass
    
    def get_member_balance_data(self, date: datetime):
        """获取指定日期的会员余额变动数据"""
        pass
```

- [ ] **Step 3: 根据API文档实现认证和各个接口**

- [ ] **Step 4: 提交代码**

```bash
cd /Users/ann/Desktop/AI/project/数据导入
git add config.py api_client.py
git commit -m "feat: add business api client config and skeleton"
```

---

## Task 2: 新增飞书通知模块

**Files:**
- Create: `utils.py` (新增通知函数)

- [ ] **Step 1: 在utils.py中新增send_feishu_notification函数**

```python
import requests
from config import FEISHU_WEBHOOK_URL

def send_feishu_notification(title, content):
    """发送飞书机器人通知"""
    if not FEISHU_WEBHOOK_URL:
        print("飞书Webhook未配置，跳过通知")
        return False
    
    message = {
        "msg_type": "text",
        "content": {
            "text": f"{title}\n\n{content}"
        }
    }
    
    try:
        resp = requests.post(FEISHU_WEBHOOK_URL, json=message)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 0:
            print("飞书通知发送成功")
            return True
        else:
            print(f"飞书通知发送失败: {result}")
            return False
    except Exception as e:
        print(f"飞书通知发送异常: {e}")
        return False
```

- [ ] **Step 2: 测试通知功能**

```python
from utils import send_feishu_notification
send_feishu_notification("测试通知", "这是一条测试消息")
```

- [ ] **Step 3: 提交代码**

```bash
git add utils.py
git commit -m "feat: add feishu notification utility"
```

---

## Task 3: 重构每日导入主脚本

**Files:**
- Modify: `scripts/daily_import.py`
- Create: `scripts/daily_import_api.py`

- [ ] **Step 1: 创建新的daily_import_api.py**

```python
#!/usr/bin/env python3
"""
每日数据导入 - API版本
从业务系统OpenAPI拉取数据，直接导入数据库
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api_client import BusinessAPIClient
from utils import send_feishu_notification
from config import LOGS_DIR

LOGS_DIR.mkdir(exist_ok=True)

def main(target_date=None):
    print("=" * 60)
    print(f"每日数据导入(API版本) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    start_time = datetime.now()
    success = True
    error_msg = ""
    
    try:
        api_client = BusinessAPIClient()
        
        # 如果没指定日期，默认拉取昨天
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        
        print(f"\n目标日期: {target_date.strftime('%Y-%m-%d')}")
        
        # 1. 拉取营业数据并导入
        print("\n【1/5】拉取日营业数据...")
        business_data = api_client.get_daily_business_data(target_date)
        # 调用现有的导入逻辑
        
        # 2. 拉取储值数据并导入
        print("\n【2/5】拉取会员储值数据...")
        recharge_data = api_client.get_member_recharge_data(target_date)
        # 调用现有的导入逻辑
        
        # 3. 拉取商品销售数据并导入
        print("\n【3/5】拉取商品销售数据...")
        product_data = api_client.get_product_sales_data(target_date)
        # 调用现有的导入逻辑
        
        # 4. 拉取订单明细并导入
        print("\n【4/5】拉取订单明细...")
        order_detail = api_client.get_order_detail_data(target_date)
        # 调用现有的导入逻辑
        
        # 5. 拉取会员余额变动并导入
        print("\n【5/5】拉取会员余额变动...")
        balance_data = api_client.get_member_balance_data(target_date)
        # 调用现有的导入逻辑
        
    except Exception as e:
        success = False
        error_msg = str(e)
        print(f"\n错误: {error_msg}")
    
    # 结束计时
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # 发送通知
    if success:
        msg = (
            f"✅ 数据导入成功\n"
            f"日期: {target_date.strftime('%Y-%m-%d')}\n"
            f"耗时: {duration:.1f}秒"
        )
        send_feishu_notification("数据导入完成", msg)
    else:
        msg = (
            f"❌ 数据导入失败\n"
            f"日期: {target_date.strftime('%Y-%m-%d')}\n"
            f"错误: {error_msg}"
        )
        send_feishu_notification("数据导入失败，请检查", msg)
    
    print("\n" + "=" * 60)
    if success:
        print("导入完成！")
    else:
        print("导入失败！")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 支持命令行指定日期
        from datetime import datetime
        target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
        main(target_date)
    else:
        main()
```

- [ ] **Step 2: 适配原有的数据导入函数**

将`import_data.py`中的数据处理和入库逻辑抽出来，让新脚本可以复用

- [ ] **Step 3: 测试单次拉取导入**

```bash
cd /Users/ann/Desktop/AI/project/数据导入
python scripts/daily_import_api.py 2026-05-13
```

- [ ] **Step 4: 验证数据库数据正确**

- [ ] **Step 5: 提交代码**

```bash
git add scripts/daily_import_api.py
git commit -m "feat: add daily import script for API"
```

---

## Task 4: 更新定时任务配置

**Files:**
- Modify: `com.ktv.dailyimport.plist`

- [ ] **Step 1: 修改定时任务，指向新的API版本脚本**

原来的：
```xml
<string>python3</string>
<string>/Users/ann/Desktop/AI/project/数据导入/scripts/daily_import.py</string>
```

改为：
```xml
<string>python3</string>
<string>/Users/ann/Desktop/AI/project/数据导入/scripts/daily_import_api.py</string>
```

- [ ] **Step 2: 重新加载定时任务**

```bash
cd /Users/ann/Desktop/AI/project/数据导入
launchctl unload ~/Library/LaunchAgents/com.ktv.dailyimport.plist
launchctl load -w ~/Library/LaunchAgents/com.ktv.dailyimport.plist
```

- [ ] **Step 3: 验证定时任务加载成功**

```bash
launchctl list | grep com.ktv.dailyimport
```

- [ ] **Step 4: 提交代码**

```bash
git add com.ktv.dailyimport.plist
git commit -m "chore: update daily import cron to API version"
```

---

## Task 5: 归档流程保持不变

**Files:** 无需修改，`daily_archive.py`保持原样

- [ ] **Step 1: 验证归档脚本仍然正常工作**

如果需要保留原始文件下载，可以继续使用归档。如果完全不需要文件了，可以考虑移除，但建议保留一段时间做双验证。

---

## Task 6: 全流程测试

- [ ] **Step 1: 手动运行完整流程测试**

```bash
cd /Users/ann/Desktop/AI/project/数据导入
python scripts/daily_import_api.py
```

- [ ] **Step 2: 检查数据库数据是否正确写入**

- [ ] **Step 3: 检查每日报表能否正常读取数据**

```bash
cd /Users/ann/Desktop/AI/project/每日_report
python generate_daily_report.py
```

- [ ] **Step 4: 检查Manpower看板能否正常读取数据**

访问Manpower看板，确认数据更新

- [ ] **Step 5: 模拟失败场景，验证通知是否正常发送**

故意填错API密钥，运行脚本，确认收到飞书通知

---

## 回滚方案

如果API对接出现问题，随时可以切回原来的文件导入方式：

```bash
# 改回原来的定时任务
cd /Users/ann/Desktop/AI/project/数据导入
launchctl unload ~/Library/LaunchAgents/com.ktv.dailyimport.plist
# 把com.ktv.dailyimport.plist改回指向daily_import.py
git checkout HEAD~1 -- com.ktv.dailyimport.plist
launchctl load -w ~/Library/LaunchAgents/com.ktv.dailyimport.plist
```

---

## 预期成果

1. ✅ 不再依赖影刀下载文件，解决了影刀不稳定问题
2. ✅ 每日自动从API拉取数据导入数据库
3. ✅ 导入失败自动发送飞书通知，及时发现问题
4. ✅ 每日报表和Manpower看板完全不需要改动，继续工作
5. ✅ 可回滚，保留原方案作为备用
