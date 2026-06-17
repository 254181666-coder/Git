"""
音频驱动服务
"""
import random
import logging
import librosa
from typing import List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class PlayMode(Enum):
    RANDOM = "random"
    SEQUENTIAL = "sequential"

class AudioDriverService:
    def __init__(self):
        self.audio_clips: List[str] = []
        self.play_mode = PlayMode.RANDOM
        self.current_index = 0
        self.is_playing = False
        
    def load_audio_clips(self, clips: List[str]):
        self.audio_clips = clips
        self.current_index = 0
        
    def set_play_mode(self, mode: str):
        self.play_mode = PlayMode(mode)
        
    def split_audio(self, input_path: str, output_dir: str, segment_duration: int = 3) -> List[str]:
        """将长音频切分为碎片化音频"""
        y, sr = librosa.load(input_path)
        total_duration = librosa.get_duration(y=y, sr=sr)
        segments = []
        
        for i in range(0, int(total_duration), segment_duration):
            start = i * sr
            end = min((i + segment_duration) * sr, len(y))
            segment = y[start:end]
            output_path = f"{output_dir}/segment_{i}.wav"
            import soundfile as sf
            sf.write(output_path, segment, sr)
            segments.append(output_path)
            
        logger.info(f"音频切分完成，共{len(segments)}段")
        return segments
        
    def get_next_clip(self) -> Optional[str]:
        if not self.audio_clips:
            return None
        if self.play_mode == PlayMode.RANDOM:
            return random.choice(self.audio_clips)
        else:
            clip = self.audio_clips[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.audio_clips)
            return clip

# 全局单例
audio_driver = AudioDriverService()