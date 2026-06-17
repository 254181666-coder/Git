"""
播助手 Pro - AI数字人直播系统
统一后端服务入口
"""
import os
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.auth import router as auth_router
from api.live import router as live_router
from api.live_mode import router as live_mode_router
from api.script import router as script_router
from api.avatar import router as avatar_router
from api.ai import router as ai_router
from api.billing import router as billing_router
from api.tts import router as tts_router
from api.compositor import router as compositor_router
from services.ai_driver import ai_driver
from services.compositor import camera_state
from services.scheduler import scheduler
from services.streaming import streaming
from services.tts import tts_service

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(title="播助手 Pro API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查（放在最前面，避免被其他路由拦截）
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/health")
async def api_health_check():
    return {"status": "healthy", "message": "播助手 Pro API运行正常"}

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>播助手 Pro API</title>
        <style>
          body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f8fb; color: #1f2937; }
          main { max-width: 960px; margin: 0 auto; padding: 40px 24px; }
          h1 { margin: 0 0 8px; font-size: 32px; }
          p { color: #5b6472; line-height: 1.7; }
          .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 24px; }
          a.card { display: block; padding: 18px; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; color: inherit; text-decoration: none; }
          a.card:hover { border-color: #1677ff; box-shadow: 0 6px 18px rgba(15, 23, 42, .08); }
          .title { font-weight: 700; margin-bottom: 6px; }
          code { background: #eef2f7; padding: 2px 6px; border-radius: 4px; }
        </style>
      </head>
      <body>
        <main>
          <h1>播助手 Pro 后端</h1>
          <p>FastAPI 服务正在运行。这里是后端状态入口，具体业务操作主要在前端控制台完成。</p>
          <div class="grid">
            <a class="card" href="/docs"><div class="title">API 文档</div><p>查看、调试所有后端接口。</p></a>
            <a class="card" href="/api/status"><div class="title">系统状态</div><p>查看直播、摄像头、AI、TTS 状态。</p></a>
            <a class="card" href="/api/health"><div class="title">健康检查</div><p>确认 API 服务可用。</p></a>
            <a class="card" href="http://localhost:3000/"><div class="title">前端控制台</div><p>打开直播系统主界面。</p></a>
          </div>
          <p>本地 RTMP 测试地址：<code>rtmp://localhost/live/test</code></p>
        </main>
      </body>
    </html>
    """

@app.get("/api/status")
async def api_status():
    current_script = scheduler.get_current_script()
    return {
        "status": "ok",
        "version": "2.0.0",
        "services": {
            "streaming": streaming.is_running(),
            "camera_running": camera_state.is_running,
            "camera_id": camera_state.camera_id,
            "camera_frames": camera_state.frame_count,
            "camera_error": camera_state.last_error,
            "scheduler": scheduler.is_running(),
            "ai_openai_connected": ai_driver.is_connected("openai"),
            "ai_sadtalker_connected": ai_driver.is_connected("sadtalker"),
            "tts_available": tts_service.is_available(),
            "tts_engine": tts_service.current_engine.value
        },
        "current_script": current_script.__dict__ if current_script else None,
        "links": {
            "frontend": "http://localhost:3000/",
            "docs": "http://localhost:8000/docs",
            "rtmp_test": "rtmp://localhost/live/test"
        }
    }

# 注册路由
app.include_router(auth_router, prefix="/api/auth", tags=["用户认证"])
app.include_router(live_router, prefix="/api/live", tags=["直播管理"])
app.include_router(live_mode_router, prefix="/api/live_mode", tags=["真人直播模式"])
app.include_router(script_router, prefix="/api/script", tags=["话术管理"])
app.include_router(avatar_router, prefix="/api/avatar", tags=["数字人驱动"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI智能"])
app.include_router(billing_router, prefix="/api/billing", tags=["计费管理"])
app.include_router(tts_router, prefix="/api/tts", tags=["TTS语音合成"])
app.include_router(compositor_router, prefix="/api/compositor", tags=["画面合成"])

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
