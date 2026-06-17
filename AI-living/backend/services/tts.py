"""
TTS语音合成服务 - 可插拔架构，支持多种TTS引擎
"""
import logging
import os
import platform
import shutil
import subprocess
import tempfile
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class TTSEngine(str, Enum):
    SYSTEM = "system"        # 系统默认（先测试用）
    DASHSCOPE = "dashscope"  # 通义千问TTS
    HAIMA = "haima"          # 海螺AI TTS
    AZURE = "azure"          # Azure TTS

class TTSService:
    """TTS服务 - 支持多引擎切换"""
    
    def __init__(self):
        self.current_engine = TTSEngine.SYSTEM
        self._init_engines()
    
    def _init_engines(self):
        """初始化各TTS引擎"""
        self.engines = {}
        
        # 系统默认（先测试用）
        self.engines[TTSEngine.SYSTEM] = SystemTTS()
        
        # 通义千问TTS（后期可接入）
        # self.engines[TTSEngine.DASHSCOPE] = DashScopeTTS()
        
        # 海螺AI TTS（后期可接入）
        # self.engines[TTSEngine.HAIMA] = HaimaTTS()
        
        logger.info(f"TTS引擎初始化完成，当前使用: {self.current_engine.value}")
    
    def set_engine(self, engine: TTSEngine):
        """切换TTS引擎"""
        if engine in self.engines:
            self.current_engine = engine
            logger.info(f"TTS引擎已切换为: {engine.value}")
        else:
            logger.warning(f"不支持的TTS引擎: {engine}")
    
    def synthesize(self, text: str, voice_id: str = "") -> Tuple[Optional[bytes], Optional[str]]:
        """合成语音"""
        engine = self.engines.get(self.current_engine)
        if not engine:
            return None, "TTS引擎未初始化"
        return engine.synthesize(text, voice_id)
    
    def list_voices(self) -> list:
        """列出可用音色"""
        engine = self.engines.get(self.current_engine)
        if not engine:
            return []
        return engine.list_voices()
    
    def is_available(self) -> bool:
        """检查TTS是否可用"""
        engine = self.engines.get(self.current_engine)
        return engine is not None and engine.is_available()


class BaseTTS:
    """TTS引擎基类"""
    
    def synthesize(self, text: str, voice_id: str = "") -> Tuple[Optional[bytes], Optional[str]]:
        raise NotImplementedError
    
    def list_voices(self) -> list:
        return []
    
    def is_available(self) -> bool:
        return True


class SystemTTS(BaseTTS):
    """系统默认TTS（先测试用）"""
    
    def synthesize(self, text: str, voice_id: str = "") -> Tuple[Optional[bytes], Optional[str]]:
        logger.info(f"SystemTTS合成: {text[:50]}...")
        if platform.system() != "Darwin":
            return None, "SystemTTS当前仅支持macOS本地say命令"
        if not shutil.which("say"):
            return None, "未找到macOS say命令"
        if not shutil.which("ffmpeg"):
            return None, "未找到FFmpeg，无法转换TTS音频"

        clean_text = text.strip()
        if not clean_text:
            return None, "合成文本不能为空"

        with tempfile.TemporaryDirectory() as tmpdir:
            aiff_path = os.path.join(tmpdir, "speech.aiff")
            wav_path = os.path.join(tmpdir, "speech.wav")
            say_cmd = ["say"]
            if voice_id and voice_id != "default":
                say_cmd.extend(["-v", voice_id])
            say_cmd.extend(["-o", aiff_path, clean_text])

            try:
                subprocess.run(say_cmd, check=True, capture_output=True, text=True, timeout=60)
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-v",
                        "error",
                        "-i",
                        aiff_path,
                        "-ar",
                        "44100",
                        "-ac",
                        "2",
                        wav_path,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                with open(wav_path, "rb") as f:
                    audio_data = f.read()
                if len(audio_data) <= 1024:
                    return None, "TTS生成了空音频，请检查macOS语音权限或改用云端TTS引擎"
                return audio_data, None
            except subprocess.CalledProcessError as e:
                return None, e.stderr.strip() or str(e)
            except subprocess.TimeoutExpired:
                return None, "TTS合成超时"
    
    def list_voices(self) -> list:
        voices = [{"id": "default", "name": "系统默认", "language": "zh-CN"}]
        if platform.system() != "Darwin" or not shutil.which("say"):
            return voices

        try:
            result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) < 2:
                    continue
                voice_id = parts[0]
                language = parts[1]
                if language.startswith("zh_") or language.startswith("zh-"):
                    voices.append({"id": voice_id, "name": voice_id, "language": language})
        except Exception:
            logger.exception("读取系统TTS音色失败")
        return voices
    
    def is_available(self) -> bool:
        return True


# 以下类为预留，后期接入

class DashScopeTTS(BaseTTS):
    """通义千问TTS（后期接入）"""
    
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
    
    def synthesize(self, text: str, voice_id: str = "") -> Tuple[Optional[bytes], Optional[str]]:
        # TODO: 接入通义千问TTS API
        return None, "通义千问TTS尚未接入"
    
    def list_voices(self) -> list:
        return [
            {"id": "xiaoyun", "name": "小云", "language": "zh-CN"},
            {"id": "xiaogang", "name": "小刚", "language": "zh-CN"},
        ]


class HaimaTTS(BaseTTS):
    """海螺AI TTS（后期接入）"""
    
    def __init__(self):
        self.api_key = os.getenv("HAIMA_API_KEY", "")
    
    def synthesize(self, text: str, voice_id: str = "") -> Tuple[Optional[bytes], Optional[str]]:
        # TODO: 接入海螺AI TTS API
        return None, "海螺AI TTS尚未接入"
    
    def list_voices(self) -> list:
        return [
            {"id": "female_warm", "name": "温暖女声", "language": "zh-CN"},
            {"id": "male_calm", "name": "沉稳男声", "language": "zh-CN"},
        ]


# 全局单例
tts_service = TTSService()
