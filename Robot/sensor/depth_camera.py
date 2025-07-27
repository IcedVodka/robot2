import pyrealsense2 as rs
import numpy as np
from collections import deque
import threading
from utils.logger import get_logger
from .vison_sensor import VisionSensor

class RealsenseSensor(VisionSensor):
    """
    RealSense相机传感器类
    基于Intel RealSense相机的传感器实现，支持多线程数据采集，
    提供彩色图像和深度图像的实时获取功能。
    """
    def __init__(self, name: str):
        super().__init__(buffer_size=1)
        self.name = name
        self.type = "realsense"
        self.logger = get_logger(self.name)
        self.pipeline = None
        self.config = None        
        self.is_depth = False

    def set_up(self, camera_serial: str, is_depth: bool = False):
        """
        设置RealSense相机
        Args:
            camera_serial: 相机序列号
            is_depth: 是否启用深度流，默认False
        Raises:
            RuntimeError: 当找不到设备或启动失败时抛出
        """
        self.is_depth = is_depth

        try:
            # 初始化RealSense上下文并检查连接的设备
            self.context = rs.context()
            self.devices = list(self.context.query_devices())
            if not self.devices:
                raise RuntimeError("No RealSense devices found")
            # 根据序列号查找设备
            device_idx = find_device_by_serial(self.devices, camera_serial)
            if device_idx is None:
                raise RuntimeError(f"Could not find camera with serial number {camera_serial}")
            # 配置管道
            self.pipeline = rs.pipeline()
            self.config = rs.config()
            # 启用指定设备
            self.config.enable_device(camera_serial)
            self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            if is_depth:
                self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            self.pipeline.start(self.config)
            self.start()
            self.logger.info(f"Started camera: {self.name} (SN: {camera_serial})")
        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to initialize camera: {str(e)}")

    def _acquire_frame(self):
        """
        采集一帧彩色/深度图像
        Returns:
            dict: {"color": 彩色图像, "depth": 深度图像}
        """
        if not self.pipeline:
            self.logger.error("Pipeline 未初始化")
            return None
        frames = self.pipeline.wait_for_frames(5000)
        result = {}
        if not self.collect_info:
            return None
        if "color" in self.collect_info:
            color_frame = frames.get_color_frame()
            if color_frame:
                color_image = np.asanyarray(color_frame.get_data())[:, :, ::-1]  # BGR->RGB
                result["color"] = color_image
        if self.is_depth and "depth" in self.collect_info:
            depth_frame = frames.get_depth_frame()
            if depth_frame:
                depth_image = np.asanyarray(depth_frame.get_data())
                result["depth"] = depth_image
        return result if result else None

    def cleanup(self):
        try:
            self.stop()
            if hasattr(self, 'pipeline') and self.pipeline:
                self.pipeline.stop()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
    
    def __del__(self):
        self.cleanup()

    def __repr__(self) -> str:
        return (f"RealsenseSensor\n"
                f"name: {self.name}\n"
                f"type: {self.type}\n"
                f"is_depth: {self.is_depth}\n"
                f"pipeline: {'initialized' if self.pipeline else 'None'}")

def find_device_by_serial(devices, serial):
    """
    根据序列号查找设备索引
    Args:
        devices: RealSense设备列表
        serial: 目标设备的序列号
    Returns:
        int: 设备在列表中的索引，如果未找到返回None
    """
    for i, dev in enumerate(devices):
        if dev.get_info(rs.camera_info.serial_number) == serial:
            return i
    return None
