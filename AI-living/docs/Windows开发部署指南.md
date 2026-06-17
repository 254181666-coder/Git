# Windows 开发部署指南

本指南用于把 AI-living 迁移到 Windows 电脑继续开发和摄像头/直播推流验证。

## 1. 推荐环境

- Windows 11
- Python 3.10 或 3.11
- Node.js LTS
- Git
- FFmpeg，并加入 `PATH`
- OBS
- 抖音直播伴侣
- USB 摄像头或采集卡

不要优先使用 WSL 做摄像头开发。摄像头、麦克风、采集卡、直播伴侣联调建议使用原生 Windows PowerShell。

## 2. Windows 权限检查

打开：

```text
设置 -> 隐私和安全性 -> 相机
```

确认：

- 相机访问：开启
- 允许应用访问相机：开启
- 允许桌面应用访问相机：开启

如果 OBS、Chrome、腾讯会议、微信会议正在占用摄像头，请先关闭。

## 3. 初始化项目

解压迁移包后，在 PowerShell 中进入项目目录：

```powershell
cd AI-living
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\windows\setup_windows.ps1
```

如果没有 Python 3.10，可以把脚本里的 `py -3.10` 改为 `py -3.11` 或 `python`。

## 4. 配置环境变量

复制：

```powershell
copy backend\.env.example backend\.env
```

然后编辑 `backend\.env`。

如果使用通义千问兼容接口，建议配置：

```env
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-turbo
```

不要把 `backend\.env` 发给别人，不要提交到 Git。

## 5. 摄像头诊断

先运行：

```powershell
.\.venv\Scripts\python.exe backend\scripts\diagnose_camera_windows.py
```

看到类似下面的输出即代表摄像头可用：

```text
OK camera_id=0 backend=DSHOW opened=True read=True shape=(1080, 1920, 3)
```

如果 `DSHOW` 不可用但 `MSMF` 可用，也可以继续。项目会自动尝试多个后端。

## 6. 启动服务

打开三个 PowerShell 窗口。

后端：

```powershell
.\scripts\windows\start_backend.ps1
```

前端：

```powershell
.\scripts\windows\start_frontend.ps1
```

本地 RTMP 测试服务：

```powershell
.\scripts\windows\start_rtmp.ps1
```

访问：

```text
http://127.0.0.1:3000
```

## 7. 本地验收顺序

1. 打开前端控制台。
2. 进入“真人直播模式”。
3. 摄像头编号先用 `0`。
4. 采集分辨率先用 `1920 x 1080` 或 `1080 x 1920`。
5. 画面适配先选 `保持比例完整`。
6. 点击开启摄像头。
7. 进入“画面合成预览”确认画面。
8. 应用零食背景和贴片：

```powershell
curl -X POST http://127.0.0.1:8000/api/compositor/background/snack_room
curl -X POST http://127.0.0.1:8000/api/compositor/overlay/snack_pack
```

9. 进入“RTMP推流”，推到本地：

```text
rtmp://127.0.0.1/live/test
```

10. 用 VLC/OBS/ffprobe 验证本地流。

## 8. 抖音试播前置验证

先用 OBS 推流到抖音，确认账号、推流地址、网络都正常。

OBS 通过后，再用本项目推流：

- 分辨率：先 `720x1280`
- 帧率：`25fps`
- 视频码率：`2000kbps`
- 音频轨：开启
- 音频码率：`128kbps`

第一轮先连续 10 分钟，第二轮再做 30 分钟稳定性测试。

## 9. 常见问题

### 摄像头打不开

- 确认 Windows 相机隐私权限已开启。
- 关闭 OBS、直播伴侣、会议软件。
- 换 `camera_id`，例如 1、2。
- 运行 `backend\scripts\diagnose_camera_windows.py` 看哪个后端可用。

### FFmpeg 不可用

在 PowerShell 运行：

```powershell
ffmpeg -version
```

如果找不到命令，需要重新安装 FFmpeg 并加入系统 `PATH`。

### Python 依赖安装失败

优先使用：

```powershell
pip install -r backend\requirements-win.txt
```

不要一开始安装完整 `backend\requirements.txt`，其中部分音频依赖在 Windows 上可能需要额外编译环境。
