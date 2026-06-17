import cv2
import numpy as np
from moviepy.editor import VideoFileClip

class LivePlay:
    def __init__(self):
        self.video_source = None
        self.is_streaming = False

    def remove_duplicate(self, frame):
        noise = np.random.normal(0, 2, frame.shape).astype(np.uint8)
        return cv2.add(frame, noise)

    def load_video(self, video_path):
        self.video_source = video_path

    def get_video_frame(self):
        if self.video_source:
            cap = cv2.VideoCapture(self.video_source)
            ret, frame = cap.read()
            cap.release()
            if ret:
                return frame
        return None

    def get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
