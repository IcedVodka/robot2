#!/usr/bin/env python3

import cv2
import logging
import numpy as np
from typing import Tuple, Optional
from Robot.sensor.depth_camera import RealsenseSensor
from grasp_task.config import GraspConfig

class ImageHandler:
    def __init__(self, config: 'GraspConfig', logger: 'logging.Logger'):
        """初始化 ImageHandler 类
        
        Args:
            config (GraspConfig): 从 grasp_task/config.py 导入的配置对象，包含相机序列号等参数
            logger (logging.Logger): 日志记录器对象，用于记录运行时信息
        """
        self.config = config
        self.logger = logger
        self.sensor = None
        self.window_name = "Grasp Control"
        self.last_color_image = None
        self.last_depth_image = None

    def setup(self):
        """初始化相机"""
        self.sensor = RealsenseSensor("hand_camera")
        self.sensor.set_up(camera_serial=self.config.camera_serial, is_depth=True)
        
        # 更新配置中的相机参数
        if self.config.update_camera_params(self.sensor):
            self.logger.info("相机参数已从传感器更新")
        else:
            self.logger.warning("无法从传感器更新相机参数，使用默认值")
            
        self.logger.info("相机初始化完成")
    
    def get_images(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """获取彩色和深度图像"""
        try:
            data = self.sensor.get_information()
            if data and "color" in data and "depth" in data:
                self.last_color_image = data["color"].copy()
                self.last_depth_image = data["depth"].copy()
                return self.last_color_image, self.last_depth_image
            return None, None
        except Exception as e:
            self.logger.error(f"获取图像失败: {str(e)}")
            return None, None

    def draw_point(self, image: np.ndarray, point: list) -> np.ndarray:
        """在图像上绘制点"""
        if point:
            x, y = point
            display_img = image.copy()
            cv2.circle(display_img, (x, y), 6, (0, 255, 0), 2)
            cv2.circle(display_img, (x, y), 1, (0, 255, 0), -1)
            
            # 显示坐标信息
            coord_text = f"({x}, {y})"
            cv2.putText(display_img, coord_text, (x+15, y-15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # 显示深度信息
            if self.last_depth_image is not None and 0 <= x < self.last_depth_image.shape[1] and 0 <= y < self.last_depth_image.shape[0]:
                depth_value = self.last_depth_image[y, x]
                depth_cm = depth_value / 10.0  # 转换为厘米
                depth_text = f"Depth: {depth_cm:.1f}cm"
                cv2.putText(display_img, depth_text, (x+15, y+5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            return display_img
        return image.copy()

    def cleanup(self):
        """清理资源"""
        if self.sensor:
            self.sensor.cleanup()
        cv2.destroyAllWindows()
