from utils.logger import get_logger
from sensor_base import Sensor
from collections import deque
import threading
from typing import Dict, Any, Optional
import numpy as np

class VisionSensor(Sensor):
    """
    视觉传感器基类
    
    继承自Sensor类，专门用于处理图像数据的传感器。
    支持彩色图像、深度图像和点云数据的采集。
    实现了多线程数据采集和帧缓冲机制，具体采集逻辑由子类实现。
    get_information：非阻塞获取队列最新帧的全部原始数据。
    get_immediate_image：阻塞采集一帧最新数据（直接调用底层采集）。
    """
    def __init__(self, buffer_size: int = 1):
        super().__init__()
        self.name = "vision_sensor"
        self.type = "vision_sensor"
        self.collect_info = None
        self.logger = get_logger(self.name)
        self.frame_buffer = deque(maxlen=buffer_size)
        self._thread = None
        self._exit_event = threading.Event()
        self._keep_running = False

    def start(self):
        if self._thread and self._thread.is_alive():
            self.logger.warning("采集线程已在运行")
            return
        self._keep_running = True
        self._exit_event.clear()
        self._thread = threading.Thread(target=self._thread_loop, daemon=True)
        self._thread.start()
        self.logger.info("采集线程已启动")

    def stop(self):
        self._keep_running = False
        self._exit_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self.logger.info("采集线程已停止")

    def _thread_loop(self):
        while not self._exit_event.is_set():
            try:
                frame = self._acquire_frame()
                if frame:
                    self.frame_buffer.append(frame)
            except Exception as e:
                self.logger.error(f"采集线程异常: {str(e)}")

    def _acquire_frame(self) -> Optional[Dict[str, np.ndarray]]:
        """
        由子类实现：采集一帧数据
        Returns:
            Dict[str, np.ndarray]: 包含图像数据的字典
        """
        raise NotImplementedError("子类必须实现 _acquire_frame() 方法")

    def get_information(self) -> Optional[Dict[str, np.ndarray]]:
        """
        非阻塞获取队列最新帧的全部原始数据
        Returns:
            Optional[Dict[str, np.ndarray]]: 最新帧全部数据
        """
        return self.frame_buffer[-1] if self.frame_buffer else None

    def get_immediate_image(self) -> Optional[Dict[str, np.ndarray]]:
        """
        阻塞采集一帧最新数据（直接调用底层采集）
        Returns:
            Optional[Dict[str, np.ndarray]]: 采集到的最新一帧全部数据
        """
        return self._acquire_frame()

    def cleanup(self):
        """
        清理传感器资源（线程清理，子类如有额外资源，必须重写并调用 super().cleanup()）
        """
        self.stop()
        # 子类如有额外资源，必须重写并调用 super().cleanup()

