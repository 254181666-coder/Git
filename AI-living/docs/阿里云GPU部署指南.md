# 阿里云GPU实例部署指南

## 第一步：创建阿里云账号

1. 访问 [阿里云官网](https://www.aliyun.com/)
2. 注册/登录账号
3. 完成实名认证
4. 充值至少¥100（用于测试）

---

## 第二步：创建GPU实例

### 2.1 进入ECS控制台

1. 登录阿里云控制台
2. 搜索"ECS云服务器"
3. 点击"创建实例"

### 2.2 配置选择

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| 地域 | 就近选择（如杭州） | 延迟低 |
| 实例规格 | `ecs.gn6v-c8g1.2xlarge` | T4 16G显存 |
| 付费模式 | **抢占式实例** | 约¥0.5/小时 |
| 操作系统 | Ubuntu 22.04 LTS | 兼容性最好 |
| 存储 | 100G 系统盘 | 足够安装SadTalker |
| 安全组 | 放开8080端口入方向 | 用于API访问 |

### 2.3 安全组配置

添加以下入方向规则：
```
端口: 8080
协议: TCP
授权对象: 0.0.0.0/0
描述: SadTalker API
```

### 2.4 设置密码

- 设置root密码（用于SSH登录）
- 记住实例的**公网IP**

---

## 第三步：连接服务器

### 3.1 SSH登录

```bash
ssh root@<你的公网IP>
```

### 3.2 安装基础依赖

```bash
# 更新系统
apt update && apt upgrade -y

# 安装必要工具
apt install -y git wget curl vim ffmpeg
```

---

## 第四步：部署SadTalker

### 4.1 克隆SadTalker代码

```bash
cd /opt
git clone https://github.com/OpenTalker/SadTalker.git
cd SadTalker
```

### 4.2 安装Python环境

```bash
# 安装Python 3.10
apt install -y python3.10 python3.10-venv python3-pip

# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate

# 安装依赖
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

### 4.3 下载预训练模型

```bash
# 下载模型文件
bash scripts/download_models.sh
```

---

## 第五步：启动SadTalker API服务

### 5.1 创建API服务脚本

创建文件 `/opt/SadTalker/server.py`：

```python
from fastapi import FastAPI, File, UploadFile, Form
import uvicorn
import os
import torch
from src.utils.preprocess import Preprocess
from src.sadtalker import SadTalker

app = FastAPI()

# 初始化SadTalker
sadtalker = None

@app.on_event("startup")
async def startup():
    global sadtalker
    sadtalker = SadTalker(lazy_load=True)

@app.post("/api/generate")
async def generate_video(
    text: str = Form(...),
    face_id: str = Form(...)
):
    # 这里实现唇形驱动逻辑
    # 1. 根据face_id找到人脸照片
    # 2. 根据text生成语音(TTS)
    # 3. 使用SadTalker生成视频
    pass

@app.post("/api/tts")
async def text_to_speech(
    text: str = Form(...),
    voice_id: str = Form(...)
):
    # TTS语音合成
    pass

@app.get("/health")
async def health_check():
    return {"status": "ok", "gpu": torch.cuda.is_available()}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8080)
```

### 5.2 启动服务

```bash
# 后台运行
nohup python server.py > sadtalker.log 2>&1 &

# 查看日志
tail -f sadtalker.log
```

---

## 第六步：验证服务

### 6.1 健康检查

```bash
curl http://localhost:8080/health
```

预期返回：
```json
{
  "status": "ok",
  "gpu": true
}
```

### 6.2 测试API

```bash
curl -X POST http://localhost:8080/api/generate \
  -F "text=欢迎使用播助手" \
  -F "face_id=test_face"
```

---

## 第七步：本地配置

### 7.1 配置.env文件

在本地项目的 `backend/.env` 中填入：

```env
AI_DRIVER_ENDPOINT=http://<你的公网IP>:8080
AI_DRIVER_API_KEY=
```

### 7.2 测试连接

```bash
cd backend
python -c "from services.ai_driver import ai_driver; print(ai_driver.is_connected('sadtalker'))"
```

---

## 常见问题

### Q1: GPU不足怎么办？

如果T4 16G不够用，可以升级：
- `ecs.gn6i-c4g1.xlarge` (A10 24G) - 约¥1/小时
- `ecs.gn7i-c8g1.2xlarge` (A100 80G) - 约¥5/小时

### Q2: 如何停止实例？

```bash
# 释放实例（不再使用）
# 在ECS控制台选择实例 → 更多 → 实例状态 → 释放设置
```

### Q3: 成本优化建议

1. **抢占式实例**比按量付费便宜60-80%
2. 测试完成后**立即释放**实例
3. 非使用时段**停止**实例（仅收存储费）

---

## 成本预估

| 配置 | 每小时成本 | 测试2小时 |
|------|-----------|-----------|
| T4 16G（抢占式） | ¥0.5 | ¥1 |
| A10 24G（抢占式） | ¥1.0 | ¥2 |
| A100 80G（抢占式） | ¥5.0 | ¥10 |

**建议先用T4 16G测试，够用且便宜。**