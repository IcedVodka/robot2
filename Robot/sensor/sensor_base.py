import threading
import queue
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
from utils.logger import get_logger


class Sensor(ABC):
    """
    传感器基类
    提供传感器的基础功能：启动、停止、数据获取等
    """
    
    def __init__(self, name: str, buffer_size: int = 10):
        """
        初始化传感器
        
        Args:
            name: 传感器名称
            buffer_size: 数据缓冲区大小
        """
        self.name = name
        self.buffer = queue.Queue(maxsize=buffer_size)
        self.running = False
        self.thread = None
        self.logger = get_logger(f"Sensor.{name}")
        
        # 传感器状态
        self.is_connected = False
        self.last_update_time = 0
        self.error_count = 0
        self.max_errors = 5
        
    def start(self) -> bool:
        """
        启动传感器
        
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
            self.thread = threading.Thread(target=self._data_collection_loop, daemon=True)
            self.thread.start()
            self.logger.info(f"{self.name} 启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"{self.name} 启动失败: {e}")
            return False
    
    def stop(self):
        """
        停止传感器
        """
        if not self.running:
            return
            
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            
        self._disconnect()
        self.logger.info(f"{self.name} 已停止")
    
    def get_latest_data(self) -> Optional[Any]:
        """
        获取最新的传感器数据
        
        Returns:
            Optional[Any]: 最新的数据，如果没有数据则返回None
        """
        try:
            if self.buffer.empty():
                return None
            return self.buffer.get_nowait()
        except queue.Empty:
            return None
    
    def is_available(self) -> bool:
        """
        检查传感器是否可用
        
        Returns:
            bool: 传感器是否可用
        """
        return self.is_connected and self.running
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取传感器状态信息
        
        Returns:
            Dict[str, Any]: 状态信息字典
        """
        return {
            "name": self.name,
            "running": self.running,
            "connected": self.is_connected,
            "buffer_size": self.buffer.qsize(),
            "error_count": self.error_count,
            "last_update": self.last_update_time
        }
    
    def clear_buffer(self):
        """
        清空数据缓冲区
        """
        while not self.buffer.empty():
            try:
                self.buffer.get_nowait()
            except queue.Empty:
                break
    
    @abstractmethod
    def _connect(self) -> bool:
        """
        连接传感器（子类必须实现）
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def _disconnect(self):
        """
        断开传感器连接（子类必须实现）
        """
        pass
    
    @abstractmethod
    def _read_data(self) -> Optional[Any]:
        """
        读取传感器数据（子类必须实现）
        
        Returns:
            Optional[Any]: 读取的数据，如果失败返回None
        """
        pass
    
    def _data_collection_loop(self):
        """
        数据采集循环
        """
        self.logger.info(f"{self.name} 开始数据采集")
        
        while self.running:
            try:
                data = self._read_data()
                if data is not None:
                    # 如果缓冲区满了，移除最旧的数据
                    if self.buffer.full():
                        try:
                            self.buffer.get_nowait()
                        except queue.Empty:
                            pass
                    
                    self.buffer.put(data)
                    self.last_update_time = time.time()
                    self.error_count = 0  # 重置错误计数
                else:
                    self.error_count += 1
                    if self.error_count >= self.max_errors:
                        self.logger.error(f"{self.name} 连续错误次数过多，停止采集")
                        break
                    time.sleep(0.01)  # 短暂等待
                    
            except Exception as e:
                self.error_count += 1
                self.logger.error(f"{self.name} 数据采集错误: {e}")
                if self.error_count >= self.max_errors:
                    self.logger.error(f"{self.name} 错误次数过多，停止采集")
                    break
                time.sleep(0.1)  # 错误时等待更长时间
        
        self.logger.info(f"{self.name} 数据采集结束")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop() 