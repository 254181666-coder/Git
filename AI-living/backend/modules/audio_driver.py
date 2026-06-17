import pyaudio
import wave
import numpy as np
import librosa
from enum import Enum

class PlayMode(Enum):
    RANDOM = "random"
    SEQUENTIAL = "sequential"

class AudioDriver:
    def __init__(self):
        self.audio_clips = []
        self.play_mode = PlayMode.RANDOM
        self.current_index = 0
        self.is_playing = False
        self.p = pyaudio.PyAudio()

    def load_audio_clips(self, clips):
        self.audio_clips = clips

    def set_play_mode(self, mode):
        self.play_mode = PlayMode(mode)

    def split_audio(self, input_path, output_dir, segment_duration=3):
        y, sr = librosa.load(input_path)
        total_duration = librosa.get_duration(y=y, sr=sr)
        segments = []
        
        for i in range(0, int(total_duration), segment_duration):
            start = i * sr
            end = min((i + segment_duration) * sr, len(y))
            segment = y[start:end]
            output_path = f"{output_dir}/segment_{i}.wav"
            librosa.output.write_wav(output_path, segment, sr)
            segments.append(output_path)
        
        return segments

    def get_next_clip(self):
        if not self.audio_clips:
            return None
        
        if self.play_mode == PlayMode.RANDOM:
            import random
            return random.choice(self.audio_clips)
        else:
            clip = self.audio_clips[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.audio_clips)
            return clip
