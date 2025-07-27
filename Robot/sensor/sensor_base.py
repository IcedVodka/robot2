from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from abc import ABC, abstractmethod

class Sensor(ABC):
    """
    基础传感器类
    
    所有传感器的基类，定义了传感器的基本接口和通用功能。
    get_information：返回传感器的全部原始信息（如最新一帧的全部数据，非阻塞，通常取队列最新帧）。
    get：根据 collect_info 过滤，只返回用户关心的数据类型。
    """
    def __init__(self):
        """初始化基础传感器"""
        self.name = "sensor"
        self.type = "sensor"
        self.collect_info: Optional[List[str]] = None
        self.logger = get_logger(self.name)
    
    def set_collect_info(self, collect_info: List[str]) -> None:
        """
        设置需要采集的数据类型
        Args:
            collect_info: 需要采集的数据类型列表，如["color", "depth"]
        """
        self.collect_info = collect_info
    
    def get(self) -> Optional[Dict[str, Any]]:
        """
        获取传感器数据（根据 collect_info 过滤）
        Returns:
            Dict[str, Any]: 包含指定类型数据的字典，如果collect_info未设置则返回全部原始数据
        """
        info = self.get_information()
        if info is None:
            self.logger.warning("get_information() 返回 None")
            return None
        if not self.collect_info:
            return info
        result = {}
        for key in self.collect_info:
            value = info.get(key)
            if value is None:
                self.logger.error(f"{key} 信息为 None 或未包含在 info 中")
                raise ValueError(f"{key} 数据为 None 或未找到")
            result[key] = value
        return result

    @abstractmethod
    def get_information(self) -> Optional[Dict[str, Any]]:
        """
        获取传感器全部原始信息
        Returns:
            Dict[str, Any]: 传感器原始数据字典
        """
        pass

    def cleanup(self):
        """
        清理传感器资源（基类只做空实现，子类如有资源需重写）
        """
        pass

    def __repr__(self) -> str:
        """返回传感器的字符串表示"""
        return f"Base Sensor, can't be used directly\nname: {self.name}\ntype: {self.type}"