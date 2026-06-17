"""
AI驱动服务 - 支持双AI驱动（SadTalker + OpenAI）
"""
import os
import aiohttp
import logging
from typing import Optional, Tuple
import openai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class AIDriverService:
    def __init__(self):
        # OpenAI配置。API Key 不是摄像头/推流测试的硬依赖，缺失时允许系统启动。
        self.openai_client = None
        self.openai_error = None
        self.openai_model = os.getenv("OPENAI_MODEL", "qwen-turbo")
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.openai_client = openai.OpenAI(
                    api_key=api_key,
                    base_url=os.getenv("OPENAI_BASE_URL")
                )
            except Exception as e:
                self.openai_error = str(e)
                logger.warning(f"OpenAI客户端初始化失败: {self.openai_error}")
        else:
            self.openai_error = "OPENAI_API_KEY未配置"
        # SadTalker配置
        self.sadtalker_endpoint = os.getenv("AI_DRIVER_ENDPOINT", "")
        self.sadtalker_api_key = os.getenv("AI_DRIVER_API_KEY", "")
        
    def generate_response(self, text: str, driver: str = "openai") -> str:
        """生成文本回复（同步）"""
        if driver == "openai":
            return self._generate_openai(text)
        elif driver == "sadtalker":
            return self._generate_sadtalker_sync(text)
        return text
        
    async def generate_response_async(self, text: str, driver: str = "openai") -> str:
        """生成文本回复（异步）"""
        if driver == "openai":
            return await self._generate_openai_async(text)
        elif driver == "sadtalker":
            return self._generate_sadtalker_sync(text)
        return text
        
    def _generate_openai(self, text: str) -> str:
        """使用OpenAI生成回复"""
        if not self.openai_client:
            logger.warning(f"OpenAI不可用: {self.openai_error}")
            return text
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "你是专业的直播带货主播"},
                    {"role": "user", "content": text}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI生成失败: {str(e)}")
            return text
            
    async def _generate_openai_async(self, text: str) -> str:
        """使用OpenAI生成回复（异步）"""
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._generate_openai, text)
        
    def _generate_sadtalker_sync(self, text: str) -> str:
        """使用SadTalker生成视频帧（同步）"""
        # 这里应该调用实际的SadTalker API
        # 暂时返回模拟数据
        logger.info(f"SadTalker生成: {text}")
        return text
        
    async def generate_video_frame(self, text: str, face_id: str) -> Tuple[Optional[bytes], Optional[str]]:
        """SadTalker生成视频帧"""
        try:
            url = f"{self.sadtalker_endpoint}/api/generate"
            payload = {"text": text, "face_id": face_id}
            headers = {}
            if self.sadtalker_api_key:
                headers["Authorization"] = f"Bearer {self.sadtalker_api_key}"
                
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        error = await resp.text()
                        return None, f"请求失败: {resp.status}"
                    data = await resp.read()
                    return data, None
        except Exception as e:
            logger.error(f"SadTalker异常: {str(e)}")
            return None, str(e)
            
    def is_connected(self, driver: str = "openai") -> bool:
        """检查AI连接状态"""
        if driver == "openai":
            return self.openai_client is not None
        elif driver == "sadtalker":
            return len(self.sadtalker_endpoint) > 0
        return False

# 全局单例
ai_driver = AIDriverService()
