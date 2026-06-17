import cv2
import numpy as np
from enum import Enum

class DriverMode(Enum):
    CAMERA = "camera"
    CACHE = "cache"
    ORIGINAL = "original"
    DUAL_AVATAR = "dual_avatar"

class AvatarDriver:
    def __init__(self):
        self.mode = DriverMode.CAMERA
        self.cap = None
        self.is_running = False

    def set_mode(self, mode):
        self.mode = DriverMode(mode)

    def start_camera(self, camera_id=0):
        self.cap = cv2.VideoCapture(camera_id)
        self.is_running = True

    def stop_camera(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_running = False

    def get_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None

    def process_frame(self, frame):
        return frame
