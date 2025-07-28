"""
RealSense传感器模块

该模块提供了基于Intel RealSense相机的传感器接口，支持多线程数据采集，
包括彩色图像、深度图像和点云数据的获取。

主要类:
- Sensor: 基础传感器类
- VisionSensor: 视觉传感器基类  
- RealsenseSensor: RealSense相机传感器实现

作者: [作者名]
版本: 1.0
"""

from utils.debug_print import debug_print
import numpy as np
import pyrealsense2 as rs
import time
from copy import copy
import threading
from collections import deque
from typing import List, Dict, Optional, Any, Union


def find_device_by_serial(devices: List[rs.device], serial: str) -> Optional[int]:
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


class Sensor:
    """
    基础传感器类
    
    所有传感器的基类，定义了传感器的基本接口和通用功能。
    """
    
    def __init__(self):
        """初始化基础传感器"""
        self.name = "sensor"
        self.type = "sensor"
        self.collect_info = None
    
    def set_collect_info(self, collect_info: List[str]) -> None:
        """
        设置需要采集的数据类型
        
        Args:
            collect_info: 需要采集的数据类型列表，如["color", "depth"]
        """
        self.collect_info = collect_info
    
    def get(self) -> Optional[Dict[str, Any]]:
        """
        获取传感器数据
        
        Returns:
            Dict[str, Any]: 包含指定类型数据的字典，如果collect_info未设置则返回None
            
        Raises:
            ValueError: 当指定类型的数据为None时抛出
        """
        if self.collect_info is None:
            debug_print({self.name}, f"collect_info is not set, if only collecting controller data, forget this warning", "WARNING")
            return None
            
        info = self.get_information()
        for collect_info in self.collect_info:
            if info[collect_info] is None:
                debug_print(f"{self.name}", f"{collect_info} information is None", "ERROR")
                raise ValueError(f"{collect_info} data is None")
                
        return {collect_info: info[collect_info] for collect_info in self.collect_info}

    def get_information(self) -> Dict[str, Any]:
        """
        获取传感器原始信息（需要子类实现）
        
        Returns:
            Dict[str, Any]: 传感器原始数据字典
        """
        raise NotImplementedError("Subclasses must implement get_information()")

    def __repr__(self) -> str:
        """返回传感器的字符串表示"""
        return f"Base Sensor, can't be used directly \n \
                name: {self.name} \n \
                type: {self.type}"
    
    def cleanup(self) -> None:
        """清理传感器资源"""
        pass


class VisionSensor(Sensor):
    """
    视觉传感器基类
    
    继承自Sensor类，专门用于处理图像数据的传感器。
    支持彩色图像、深度图像和点云数据的采集。
    """
    
    def __init__(self):
        """初始化视觉传感器"""
        super().__init__()
        self.name = "vision_sensor"
        self.type = "vision_sensor"
        self.collect_info = None

    def get_information(self) -> Dict[str, np.ndarray]:
        """
        获取视觉传感器信息
        
        Returns:
            Dict[str, np.ndarray]: 包含图像数据的字典
                - "color": BGR彩色图像 (H, W, 3)，与OpenCV格式保持一致
                - "depth": 深度图像 (H, W)，单位为毫米(mm)
                - "point_cloud": 点云数据 (N, 3)
        """
        image_info = {}
        image = self.get_image()
        
        if "color" in self.collect_info:
            image_info["color"] = image["color"]
        if "depth" in self.collect_info:
            image_info["depth"] = image["depth"]
        if "point_cloud" in self.collect_info:
            image_info["point_cloud"] = image["point_cloud"]
        
        return image_info
    
    def get_image(self) -> Dict[str, np.ndarray]:
        """
        获取图像数据（需要子类实现）
        
        Returns:
            Dict[str, np.ndarray]: 包含图像数据的字典
        """
        raise NotImplementedError("Subclasses must implement get_image()")


class RealsenseSensor(VisionSensor):
    """
    RealSense相机传感器类
    
    基于Intel RealSense相机的传感器实现，支持多线程数据采集，
    提供彩色图像和深度图像的实时获取功能。
    
    特性:
    - 支持多线程异步数据采集
    - 输出BGR格式图像，与OpenCV保持一致
    - 线程安全的帧缓冲机制
    - 优雅的资源清理
    """
    
    def __init__(self, name: str):
        """
        初始化RealSense传感器
        
        Args:
            name: 传感器名称，用于标识不同的相机实例
        """
        super().__init__()
        self.name = name
        self.is_depth = False
        
        # 多线程相关变量
        self.frame_buffer = deque(maxlen=1)  # 仅保留最新帧
        self.keep_running = False
        self.exit_event = threading.Event()
        self.thread = None
        
        # RealSense相关变量
        self.context = None
        self.pipeline = None
        self.config = None
        
    def set_up(self, camera_serial: str, is_depth: bool = False) -> None:
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
            
            # 启用彩色流
            self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            
            # 如果启用深度，则配置深度流
            if is_depth:
                self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            
            # 启动流并开始多线程采集
            try:
                self.pipeline.start(self.config)
                self._start_threading()
                print(f"Started camera: {self.name} (SN: {camera_serial})")
            except RuntimeError as e:
                raise RuntimeError(f"Error starting camera: {str(e)}")
                
        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to initialize camera: {str(e)}")

    def _start_threading(self) -> None:
        """启动多线程数据采集"""
        self.keep_running = True
        self.exit_event.clear()
        self.thread = threading.Thread(target=self._update_frames)
        self.thread.daemon = True
        self.thread.start()

    def get_image(self) -> Dict[str, np.ndarray]:
        """
        同步获取图像数据（阻塞方式）
        
        Returns:
            Dict[str, np.ndarray]: 包含图像数据的字典
                - "color": RGB彩色图像 (H, W, 3)
                - "depth": 深度图像 (H, W)
                
        Raises:
            RuntimeError: 当获取帧失败时抛出
            ValueError: 当深度流未启用但请求深度数据时抛出
        """
        image = {}
        frame = self.pipeline.wait_for_frames()

        if "color" in self.collect_info:
            color_frame = frame.get_color_frame()
            if not color_frame:
                raise RuntimeError("Failed to get color frame.")
            # RealSense默认输出BGR格式，直接使用，与OpenCV保持一致
            color_image = np.asanyarray(color_frame.get_data()).copy()
            image["color"] = color_image

        if "depth" in self.collect_info:
            if not self.is_depth:
                debug_print(self.name, f"should use set_up(is_depth=True) to enable collecting depth image", "ERROR")
                raise ValueError("Depth stream not enabled")
            else:       
                depth_frame = frame.get_depth_frame()
                if not depth_frame:
                    raise RuntimeError("Failed to get depth frame.")
                depth_image = np.asanyarray(depth_frame.get_data()).copy()
                image["depth"] = depth_image
                
        return image

    def _update_frames(self) -> None:
        """
        独立线程持续获取帧数据
        
        该方法在独立线程中运行，持续从RealSense相机获取帧数据
        并存储到线程安全的缓冲区中。
        """
        try:
            while not self.exit_event.is_set():
                frames = self.pipeline.wait_for_frames(5000)  # 5秒超时
                
                # 分离颜色和深度帧
                frame_data = {}
                
                if "color" in self.collect_info:
                    color_frame = frames.get_color_frame()
                    if color_frame:
                        # RealSense默认输出BGR格式，直接使用，与OpenCV保持一致
                        frame_data["color"] = np.asanyarray(color_frame.get_data())
                
                if self.is_depth and "depth" in self.collect_info:
                    depth_frame = frames.get_depth_frame()
                    if depth_frame:
                        frame_data["depth"] = np.asanyarray(depth_frame.get_data())
                
                if frame_data:
                    self.frame_buffer.append(frame_data)
                    
        except RuntimeError as e:
            if "timeout" in str(e):
                print(f"{self.name} 帧等待超时，重试中...")
            else:
                raise
        except Exception as e:
            print(f"{self.name} 捕获异常: {str(e)}")
    
    def get_image_mp(self) -> Optional[Dict[str, np.ndarray]]:
        """
        非阻塞获取最新帧数据
        
        Returns:
            Optional[Dict[str, np.ndarray]]: 最新的帧数据，如果没有数据则返回None
        """
        return self.frame_buffer[-1] if self.frame_buffer else None
    
    def cleanup(self) -> None:
        """
        清理传感器资源（同步版本）
        
        停止RealSense管道并释放相关资源。
        """
        try:
            if hasattr(self, 'pipeline') and self.pipeline:
                self.pipeline.stop()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
    
    def cleanup_mp(self) -> None:
        """
        清理传感器资源（多线程版本）
        
        优雅地停止多线程数据采集并清理资源。
        """
        # 设置退出标志
        self.exit_event.set()
        self.keep_running = False
        
        # 等待线程结束
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            
        # 停止管道
        if hasattr(self, 'pipeline') and self.pipeline:
            self.pipeline.stop()
    
    def __del__(self):
        """析构函数，确保资源被正确释放"""
        self.cleanup()


def main():
    """
    主函数 - 演示RealSense传感器的使用
    
    该函数展示了如何初始化两个RealSense相机，
    并持续采集图像数据。
    """
    # 创建传感器实例
    topcam = RealsenseSensor("top")
    handcam = RealsenseSensor("hand")

    # 设置相机参数
    topcam.set_up("207522073950", is_depth=True)
    handcam.set_up("327122078945", is_depth=True)
    
    # 设置采集的数据类型
    topcam.set_collect_info(["color", "depth"])
    handcam.set_collect_info(["color", "depth"])

    # 数据存储列表
    cam_list = []
    cam_list1 = []

    try:
        # 持续采集数据
        for i in range(500):
            print(f"采集第 {i} 帧")
            
            # 获取图像数据
            data = topcam.get_image_mp()
            data1 = handcam.get_image_mp()
            
            # 存储数据
            cam_list.append(data)
            cam_list1.append(data1)
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("用户中断，正在清理资源...")
    finally:
        # 清理资源
        topcam.cleanup_mp()
        handcam.cleanup_mp()
        print("资源清理完成")


if __name__ == "__main__":
    main()
