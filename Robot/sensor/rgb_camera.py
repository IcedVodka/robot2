import cv2
import numpy as np
from .vison_sensor import VisionSensor
from utils.logger import get_logger

class RgbCameraSensor(VisionSensor):
    def __init__(self, camera_id=0):
        super().__init__(buffer_size=1)
        self.camera_id = camera_id
        self.cap = None
        self.name = f"rgb_camera_{camera_id}"
        self.type = "rgb_camera"
        self.logger = get_logger(self.name)

    def set_up(self):
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 {self.camera_id}")
        self.start()

    def _acquire_frame(self):
        if self.cap is None or not self.cap.isOpened():
            self.logger.error("摄像头未初始化")
            return None
        ret, frame = self.cap.read()
        if not ret:
            self.logger.error("读取摄像头帧失败")
            return None
        return {"color": frame}

    def cleanup(self):
        self.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
