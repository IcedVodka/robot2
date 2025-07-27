"""
深度相机模块

该模块提供了基于Intel RealSense相机的深度相机接口，支持多线程数据采集，
包括彩色图像、深度图像和点云数据的获取。

主要类:
- DepthCamera: 深度相机传感器类

作者: [作者名]
版本: 1.0
"""

import cv2
import numpy as np
import pyrealsense2 as rs
import time
import threading
from collections import deque
from typing import Optional, Tuple, Dict, Any, Union, List
from .sensor_base import Sensor


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


class DepthCamera(Sensor):
    """
    深度相机传感器类
    
    基于Intel RealSense相机的深度相机实现，支持多线程数据采集，
    提供彩色图像、深度图像和点云数据的实时获取功能。
    
    特性:
    - 支持多线程异步数据采集
    - 自动BGR到RGB颜色空间转换
    - 线程安全的帧缓冲机制
    - 支持相机内参和外参管理
    - 支持手眼标定结果
    - 优雅的资源清理
    """
    
    def __init__(self, name: str, serial_number: Optional[str] = None, 
                 width: int = 640, height: int = 480, fps: int = 30,
                 buffer_size: int = 10, enable_color: bool = True, 
                 enable_depth: bool = True,
                 color_intrinsics: Optional[Dict] = None,
                 depth_intrinsics: Optional[Dict] = None,
                 hand_eye_calibration: Optional[Dict] = None):
        """
        初始化深度相机
        
        Args:
            name: 相机名称
            serial_number: 设备序列号，如果为None则使用第一个可用设备
            width: 图像宽度
            height: 图像高度
            fps: 帧率
            buffer_size: 缓冲区大小
            enable_color: 是否启用彩色流
            enable_depth: 是否启用深度流
            enable_ir: 是否启用红外流
            color_intrinsics: 彩色相机内参
            depth_intrinsics: 深度相机内参
            hand_eye_calibration: 手眼标定结果
        """
        super().__init__(name=name, buffer_size=buffer_size)
        
        # 相机配置参数
        self.serial_number = serial_number
        self.width = width
        self.height = height
        self.fps = fps
        self.enable_color = enable_color
        self.enable_depth = enable_depth

        
        # 相机内参和外参
        self.color_intrinsics = color_intrinsics
        self.depth_intrinsics = depth_intrinsics
        self.hand_eye_calibration = hand_eye_calibration
        
        # RealSense相关对象
        self.pipeline = None
        self.config = None
        self.device = None
        self.device_index = None
        self.context = None
        
        # 多线程相关变量
        self.frame_buffer = deque(maxlen=1)  # 仅保留最新帧
        self.keep_running = False
        self.exit_event = threading.Event()
        self.thread = None
        
        # 相机参数
        self.frame_count = 0
        self.fps_actual = 0
        self.last_fps_time = 0
        self.depth_scale = None
        
        # 数据采集类型
        self.collect_info = []
        if enable_color:
            self.collect_info.append("color")
        if enable_depth:
            self.collect_info.append("depth")

        
    def _connect(self) -> bool:
        """
        连接深度相机设备
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 创建RealSense上下文
            self.context = rs.context()
            devices = self.context.query_devices()
            
            if len(devices) == 0:
                self.logger.error("未找到RealSense设备")
                return False
            
            # 查找指定序列号的设备
            if self.serial_number is not None:
                self.device_index = find_device_by_serial(devices, self.serial_number)
                if self.device_index is None:
                    self.logger.error(f"未找到序列号为 {self.serial_number} 的设备")
                    return False
                self.device = devices[self.device_index]
                self.logger.info(f"找到设备: {self.device.get_info(rs.camera_info.name)} "
                               f"(序列号: {self.serial_number})")
            else:
                # 使用第一个可用设备
                self.device_index = 0
                self.device = devices[0]
                self.serial_number = self.device.get_info(rs.camera_info.serial_number)
                self.logger.info(f"使用第一个设备: {self.device.get_info(rs.camera_info.name)} "
                               f"(序列号: {self.serial_number})")
            
            # 创建配置
            self.config = rs.config()
            self.config.enable_device(self.serial_number)
            
            # 配置数据流
            if self.enable_color:
                self.config.enable_stream(rs.stream.color, self.width, self.height, 
                                       rs.format.bgr8, self.fps)
            
            if self.enable_depth:
                self.config.enable_stream(rs.stream.depth, self.width, self.height, 
                                       rs.format.z16, self.fps)
            
            
            # 创建管道并启动
            self.pipeline = rs.pipeline()
            profile = self.pipeline.start(self.config)
            
            # 获取深度比例因子
            if self.enable_depth:
                depth_sensor = self.device.first_depth_sensor()
                self.depth_scale = depth_sensor.get_depth_scale()
                self.logger.info(f"深度比例因子: {self.depth_scale}")
            
            # 获取实际的内参（如果未提供）
            if self.enable_color and self.color_intrinsics is None:
                color_profile = profile.get_stream(rs.stream.color)
                intrinsics = color_profile.as_video_stream_profile().get_intrinsics()
                self.color_intrinsics = {
                    'ppx': intrinsics.ppx,
                    'ppy': intrinsics.ppy,
                    'fx': intrinsics.fx,
                    'fy': intrinsics.fy
                }
            
            if self.enable_depth and self.depth_intrinsics is None:
                depth_profile = profile.get_stream(rs.stream.depth)
                intrinsics = depth_profile.as_video_stream_profile().get_intrinsics()
                self.depth_intrinsics = {
                    'ppx': intrinsics.ppx,
                    'ppy': intrinsics.ppy,
                    'fx': intrinsics.fx,
                    'fy': intrinsics.fy
                }
            
            self.logger.info(f"深度相机 {self.name} 连接成功")
            self.logger.info(f"分辨率: {self.width}x{self.height}, 帧率: {self.fps}")
            self.logger.info(f"采集数据类型: {self.collect_info}")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            self.logger.error(f"连接深度相机 {self.name} 失败: {e}")
            return False
    
    def _disconnect(self):
        """
        断开深度相机连接
        """
        try:
            # 停止多线程采集
            if hasattr(self, 'keep_running') and self.keep_running:
                self.keep_running = False
                self.exit_event.set()
                if self.thread and self.thread.is_alive():
                    self.thread.join(timeout=2.0)
            
            # 停止管道
            if self.pipeline is not None:
                self.pipeline.stop()
                self.pipeline = None
            
            # 清理资源
            self.config = None
            self.device = None
            self.context = None
            self.is_connected = False
            self.logger.info(f"深度相机 {self.name} 已断开连接")
            
        except Exception as e:
            self.logger.error(f"断开深度相机连接时出错: {e}")
    
    def _read_data(self) -> Optional[Dict[str, Any]]:
        """
        读取深度相机数据
        
        Returns:
            Optional[Dict[str, Any]]: 包含深度数据和元信息的字典
        """
        try:
            if self.pipeline is None:
                return None
            
            # 等待数据帧
            frames = self.pipeline.wait_for_frames(timeout_ms=5000)
            
            # 更新帧计数和帧率
            current_time = time.time()
            self.frame_count += 1
            
            if current_time - self.last_fps_time >= 1.0:
                self.fps_actual = self.frame_count / (current_time - self.last_fps_time)
                self.frame_count = 0
                self.last_fps_time = current_time
            
            # 构建数据字典
            data = {
                'timestamp': current_time,
                'camera_name': self.name,
                'serial_number': self.serial_number,
                'width': self.width,
                'height': self.height,
                'fps_actual': self.fps_actual,
                'frame_count': self.frame_count,
                'color_intrinsics': self.color_intrinsics,
                'depth_intrinsics': self.depth_intrinsics,
                'hand_eye_calibration': self.hand_eye_calibration,
                'depth_scale': self.depth_scale
            }
            
            # 获取彩色图像
            if self.enable_color:
                color_frame = frames.get_color_frame()
                if color_frame:
                    color_image = np.asanyarray(color_frame.get_data())
                    # BGR -> RGB 转换
                    data['color_frame'] = color_image[:,:,::-1]
            
            # 获取深度图像
            if self.enable_depth:
                depth_frame = frames.get_depth_frame()
                if depth_frame:
                    depth_image = np.asanyarray(depth_frame.get_data())
                    data['depth_frame'] = depth_image
                    
                    # 生成点云数据（可选）
                    if self.depth_scale is not None:
                        # 创建点云
                        pc = rs.pointcloud()
                        points = pc.calculate(depth_frame)
                        vertices = points.get_vertices()
                        point_cloud = np.asanyarray(vertices).reshape(self.height, self.width, 3)
                        data['point_cloud'] = point_cloud           

            
            return data
            
        except Exception as e:
            self.logger.error(f"读取深度相机数据失败: {e}")
            return None
    
    def get_latest_color_frame(self) -> Optional[np.ndarray]:
        """
        获取最新的彩色图像
        
        Returns:
            Optional[np.ndarray]: RGB格式的彩色图像，如果未启用彩色流则返回None
        """
        data = self.get_latest_data()
        if data and 'color_frame' in data:
            return data['color_frame']
        return None
    
    def get_latest_depth_frame(self) -> Optional[np.ndarray]:
        """
        获取最新的深度图像
        
        Returns:
            Optional[np.ndarray]: 深度图像，如果未启用深度流则返回None
        """
        data = self.get_latest_data()
        if data and 'depth_frame' in data:
            return data['depth_frame']
        return None    

    
    def get_latest_data_with_info(self) -> Optional[Dict[str, Any]]:
        """
        获取最新的完整数据（包括元信息）
        
        Returns:
            Optional[Dict[str, Any]]: 完整的数据字典
        """
        return self.get_latest_data()
    
    def get_camera_info(self) -> Dict[str, Any]:
        """
        获取相机信息
        
        Returns:
            Dict[str, Any]: 相机信息字典
        """
        info = super().get_status()
        info.update({
            'serial_number': self.serial_number,
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'enable_color': self.enable_color,
            'enable_depth': self.enable_depth,
            'enable_ir': self.enable_ir,
            'color_intrinsics': self.color_intrinsics,
            'depth_intrinsics': self.depth_intrinsics,
            'hand_eye_calibration': self.hand_eye_calibration,
            'depth_scale': self.depth_scale,
            'collect_info': self.collect_info
        })
        return info
    
    def get_depth_scale(self) -> Optional[float]:
        """
        获取深度比例因子
        
        Returns:
            Optional[float]: 深度比例因子，用于将深度值转换为米
        """
        return self.depth_scale
    
    def set_collect_info(self, collect_info: List[str]) -> None:
        """
        设置需要采集的数据类型
        
        Args:
            collect_info: 需要采集的数据类型列表，如["color", "depth"]
        """
        self.collect_info = collect_info
        self.logger.info(f"设置采集数据类型: {collect_info}")
    
    
    def _start_threading(self) -> None:
        """启动多线程数据采集"""
        self.keep_running = True
        self.exit_event.clear()
        self.thread = threading.Thread(target=self._update_frames)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info(f"启动多线程数据采集: {self.name}")

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
                
                if "color" in self.collect_info and self.enable_color:
                    color_frame = frames.get_color_frame()
                    if color_frame:
                        # BGR -> RGB 转换
                        frame_data["color"] = np.asanyarray(color_frame.get_data())[:,:,::-1]
                
                if "depth" in self.collect_info and self.enable_depth:
                    depth_frame = frames.get_depth_frame()
                    if depth_frame:
                        frame_data["depth"] = np.asanyarray(depth_frame.get_data())
                
                if "ir" in self.collect_info and self.enable_ir:
                    ir_frame = frames.get_infrared_frame()
                    if ir_frame:
                        frame_data["ir"] = np.asanyarray(ir_frame.get_data())
                
                if frame_data:
                    self.frame_buffer.append(frame_data)
                    
        except RuntimeError as e:
            if "timeout" in str(e):
                self.logger.warning(f"{self.name} 帧等待超时，重试中...")
            else:
                self.logger.error(f"{self.name} 多线程采集错误: {e}")
        except Exception as e:
            self.logger.error(f"{self.name} 捕获异常: {str(e)}")
    
    def start_with_threading(self) -> bool:
        """
        启动带多线程的深度相机
        
        Returns:
            bool: 启动是否成功
        """
        if self.running:
            self.logger.warning(f"{self.name} 已经在运行")
            return True
            
        try:
            if not self._connect():
                self.logger.error(f"{self.name} 连接失败")
                return False
                
            self.running = True
            self._start_threading()
            self.logger.info(f"{self.name} 启动成功（多线程模式）")
            return True
            
        except Exception as e:
            self.logger.error(f"{self.name} 启动失败: {e}")
            return False
    
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
        self.cleanup_mp()


def list_available_devices():
    """
    列出所有可用的RealSense设备并打印信息
    """
    try:
        ctx = rs.context()
        rs_devices = ctx.query_devices()
        
        if not rs_devices:
            print("未找到可用的RealSense设备")
            return
        
        print(f"找到 {len(rs_devices)} 个RealSense设备:")
        print("-" * 60)
        
        for i, device in enumerate(rs_devices, 1):
            try:
                name = device.get_info(rs.camera_info.name)
                serial_number = device.get_info(rs.camera_info.serial_number)
                firmware_version = device.get_info(rs.camera_info.firmware_version)
                usb_type = device.get_info(rs.camera_info.usb_type_descriptor)
                
                print(f"设备 {i}:")
                print(f"  名称: {name}")
                print(f"  序列号: {serial_number}")
                print(f"  固件版本: {firmware_version}")
                print(f"  USB类型: {usb_type}")
                print()
                
            except Exception as e:
                print(f"设备 {i} 信息获取失败: {e}")
                print()
        
        print("-" * 60)
        
    except Exception as e:
        print(f"获取设备列表失败: {e}")
    finally:
        # 确保释放资源
        try:
            if 'ctx' in locals():
                del ctx
        except:
            pass


def create_depth_camera_from_config(config: Dict[str, Any]) -> DepthCamera:
    """
    从配置文件创建深度相机
    
    Args:
        config: 配置字典，包含深度相机的配置参数
        
    Returns:
        DepthCamera: 深度相机实例
    """
    name = config.get('name', 'DepthCamera')
    serial_number = config.get('serial_number')
    width = config.get('width', 640)
    height = config.get('height', 480)
    fps = config.get('fps', 30)
    buffer_size = config.get('buffer_size', 10)
    enable_color = config.get('enable_color', True)
    enable_depth = config.get('enable_depth', True)
    enable_ir = config.get('enable_ir', False)
    
    # 获取内参和外参
    color_intrinsics = config.get('color_intrinsics')
    depth_intrinsics = config.get('depth_intrinsics')
    hand_eye_calibration = config.get('hand_eye_calibration')
    
    return DepthCamera(
        name=name,
        serial_number=serial_number,
        width=width,
        height=height,
        fps=fps,
        buffer_size=buffer_size,
        enable_color=enable_color,
        enable_depth=enable_depth,
        enable_ir=enable_ir,
        color_intrinsics=color_intrinsics,
        depth_intrinsics=depth_intrinsics,
        hand_eye_calibration=hand_eye_calibration
    )


def main():
    """
    主函数 - 演示深度相机的使用
    
    该函数展示了如何初始化深度相机并持续采集图像数据。
    """
    # 列出可用设备
    print("可用设备:")
    list_available_devices()
    
    # 创建深度相机实例
    camera = DepthCamera(
        name="TestCamera",
        serial_number="327122072195",  # 使用配置文件中的序列号
        width=640,
        height=480,
        fps=30,
        enable_color=True,
        enable_depth=True,
        enable_ir=False
    )
    
    # 设置采集的数据类型
    camera.set_collect_info(["color", "depth"])
    
    try:
        # 启动相机
        if camera.start_with_threading():
            print("相机启动成功，开始采集数据...")
            
            # 持续采集数据
            for i in range(100):
                # 获取图像数据
                data = camera.get_image_mp()
                if data:
                    print(f"采集第 {i} 帧 - 彩色图像: {data.get('color', 'None').shape if 'color' in data else 'None'}, "
                          f"深度图像: {data.get('depth', 'None').shape if 'depth' in data else 'None'}")
                else:
                    print(f"采集第 {i} 帧 - 无数据")
                
                time.sleep(0.1)
                
        else:
            print("相机启动失败")
            
    except KeyboardInterrupt:
        print("用户中断，正在清理资源...")
    finally:
        # 清理资源
        camera.cleanup_mp()
        print("资源清理完成")


if __name__ == "__main__":
    main()


