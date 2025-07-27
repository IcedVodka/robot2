import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any
from .sensor_base import Sensor
import time


class RGBCamera(Sensor):
    """
    RGB相机传感器类
    使用OpenCV读取相机数据并放入队列
    """
    
    def __init__(self, camera_id: int = 0, width: int = 640, height: int = 480, 
                 fps: int = 30, buffer_size: int = 10):
        """
        初始化RGB相机
        
        Args:
            camera_id: 相机设备ID
            width: 图像宽度
            height: 图像高度
            fps: 帧率
            buffer_size: 缓冲区大小
        """
        super().__init__(name=f"RGBCamera_{camera_id}", buffer_size=buffer_size)
        
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        
        # 相机参数
        self.frame_count = 0
        self.fps_actual = 0
        self.last_fps_time = 0
        
    def _connect(self) -> bool:
        """
        连接相机设备
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                self.logger.error(f"无法打开相机 {self.camera_id}")
                return False
            
            # 设置相机参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # 验证设置是否生效
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(f"相机 {self.camera_id} 连接成功")
            self.logger.info(f"分辨率: {actual_width}x{actual_height}, 帧率: {actual_fps:.1f}")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            self.logger.error(f"连接相机 {self.camera_id} 失败: {e}")
            return False
    
    def _disconnect(self):
        """
        断开相机连接
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_connected = False
        self.logger.info(f"相机 {self.camera_id} 已断开连接")
    
    def _read_data(self) -> Optional[Dict[str, Any]]:
        """
        读取相机数据
        
        Returns:
            Optional[Dict[str, Any]]: 包含图像数据和元信息的字典，格式如下：
                {
                    'frame': np.ndarray,      # BGR格式的图像数据，形状为(height, width, 3)，数据类型uint8
                    'timestamp': float,        # 图像获取时间戳（Unix时间戳，秒）
                    'camera_id': int,          # 相机设备ID
                    'width': int,              # 图像宽度（像素）
                    'height': int,             # 图像高度（像素）
                    'fps_actual': float,       # 实际帧率（每秒更新一次）
                    'frame_count': int         # 帧计数器（每秒重置）
                }
                
        Notes:
            - 图像格式为BGR，这是OpenCV的默认格式
            - 图像数据类型为uint8，像素值范围0-255
            - 如果相机未连接或读取失败，返回None
            - fps_actual通过计算每秒的帧数得出，用于监控实际性能
            - timestamp用于记录数据获取的精确时间
        """
        if self.cap is None or not self.cap.isOpened():
            return None
        
        try:
            ret, frame = self.cap.read()
            if not ret:
                self.logger.warning(f"相机 {self.camera_id} 读取帧失败")
                return None
            
            # 计算实际帧率
            current_time = time.time()
            self.frame_count += 1
            if current_time - self.last_fps_time >= 1.0:  # 每秒更新一次FPS
                self.fps_actual = self.frame_count / (current_time - self.last_fps_time)
                self.frame_count = 0
                self.last_fps_time = current_time
            
            # 创建数据字典
            data = {
                'frame': frame,
                'timestamp': current_time,
                'camera_id': self.camera_id,
                'width': frame.shape[1],
                'height': frame.shape[0],
                'fps_actual': self.fps_actual,
                'frame_count': self.frame_count
            }
            
            return data
            
        except Exception as e:
            self.logger.error(f"读取相机数据错误: {e}")
            return None
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        获取最新的图像帧（非阻塞）
        
        Returns:
            Optional[np.ndarray]: 最新的图像帧，如果没有数据则返回None
            
        Notes:
            - 返回的图像格式为 BGR (Blue-Green-Red)，这是OpenCV的默认格式
            - 图像形状为 (height, width, 3)，数据类型为 uint8
            - 如果需要RGB格式，需要调用 cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            - 图像数据是numpy数组，可以直接用于OpenCV操作
            - 如果相机未连接或读取失败，返回None
        """
        data = self.get_latest_data()
        if data is not None:
            return data['frame']
        return None
    
    def get_latest_data_with_info(self) -> Optional[Dict[str, Any]]:
        """
        获取最新的图像数据及其元信息（非阻塞）
        
        Returns:
            Optional[Dict[str, Any]]: 包含图像和元信息的字典，格式如下：
                {
                    'frame': np.ndarray,      # BGR格式的图像数据，形状为(height, width, 3)
                    'timestamp': float,        # 图像获取时间戳（秒）
                    'camera_id': int,          # 相机设备ID
                    'width': int,              # 图像宽度
                    'height': int,             # 图像高度
                    'fps_actual': float,       # 实际帧率
                    'frame_count': int         # 帧计数器
                }
                
        Notes:
            - 图像格式为BGR，如需RGB格式请使用cv2.cvtColor转换
            - timestamp是Unix时间戳，精度为秒
            - fps_actual是实时计算的实际帧率，每秒更新一次
            - 如果相机未连接或读取失败，返回None
            - 数据来自缓冲区，可能不是最新的实时数据
        """
        return self.get_latest_data()
    
    def get_camera_info(self) -> Dict[str, Any]:
        """
        获取相机信息
        
        Returns:
            Dict[str, Any]: 相机信息字典，包含以下字段：
                {
                    'name': str,               # 传感器名称
                    'is_connected': bool,       # 连接状态
                    'is_running': bool,         # 运行状态
                    'buffer_size': int,         # 缓冲区大小
                    'data_count': int,          # 当前缓冲区中的数据数量
                    'camera_id': int,           # 相机设备ID
                    'width': int,               # 设置的图像宽度
                    'height': int,              # 设置的图像高度
                    'fps': int,                 # 设置的帧率
                    'fps_actual': float         # 实际帧率
                }
                
        Notes:
            - 此方法返回相机的完整状态信息
            - fps_actual是实时计算的实际帧率，可能与设置的fps不同
            - 如果相机未连接，is_connected为False
            - buffer_size表示数据缓冲区的大小，用于平滑数据流
        """
        info = self.get_status()
        info.update({
            'camera_id': self.camera_id,
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'fps_actual': self.fps_actual
        })
        return info


def create_rgb_camera_from_config(config: Dict[str, Any]) -> RGBCamera:
    """
    根据配置文件创建RGB相机实例
    
    Args:
        config: 相机配置字典，包含以下可选字段：
            {
                'camera_id': int,      # 相机设备ID，默认为0
                'width': int,           # 图像宽度，默认为640
                'height': int,          # 图像高度，默认为480
                'fps': int,             # 帧率，默认为30
                'buffer_size': int      # 缓冲区大小，默认为10
            }
        
    Returns:
        RGBCamera: RGB相机实例
        
    Notes:
        - 如果配置字典中缺少某个参数，将使用默认值
        - camera_id通常为0表示第一个相机，1表示第二个相机，以此类推
        - width和height必须是相机支持的分辨率
        - fps设置可能受硬件限制，实际帧率可能不同
        - buffer_size影响内存使用和数据延迟，建议根据应用需求调整
    """
    camera_id = config.get('camera_id', 0)
    width = config.get('width', 640)
    height = config.get('height', 480)
    fps = config.get('fps', 30)
    buffer_size = config.get('buffer_size', 10)
    
    return RGBCamera(
        camera_id=camera_id,
        width=width,
        height=height,
        fps=fps,
        buffer_size=buffer_size
    )


