#!/usr/bin/env python3

import cv2
import numpy as np
import tempfile
import os
from typing import List, Optional, Tuple, Any
import logging
from utils.llm_quest import VisionAPI, ImageInput
from grasp_task.image_handler import ImageHandler
import time

class PointSelector:
    """点选择器类，用于手动或AI辅助选择图像中的点"""
    
    def __init__(self, image_handler: ImageHandler, logger: logging.Logger) -> None:
        """
        初始化点选择器
        
        Args:
            image_handler: 图像处理器对象，需要实现 get_images() 和 draw_point() 方法
            logger: 日志记录器对象，用于记录操作日志
        """
        self.image_handler = image_handler
        self.logger = logger
        self.selected_point: List[int] = [320, 240]  # 默认中心点
        self.window_name: str = "Point Selection"
        self.vision_api = VisionAPI()

    def mouse_callback(self, event: int, x: int, y: int, flags: int, param: Any) -> None:
        """
        鼠标事件回调函数
        
        Args:
            event: OpenCV鼠标事件类型
            x: 鼠标x坐标
            y: 鼠标y坐标
            flags: 鼠标事件标志
            param: 额外参数
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            self.selected_point = [x, y]
            self.logger.info(f"用户选择点: ({x}, {y})")

    def manual_select(self) -> bool:
        """
        手动选择点
        
        允许用户通过鼠标点击选择目标点
        
        Returns:
            bool: 是否成功选择点（True表示成功，False表示用户取消）
        """
        self.logger.info("进入手动选择模式")
        self.logger.info("点击选择目标点，默认中心点，回车进入下一阶段, ESC退出程序")

        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        while True:
            color_img, _ = self.image_handler.get_images()
            if color_img is None:
                self.logger.warning("无法获取图像，重试中...")
                continue
            
            display_img = self.image_handler.draw_point(color_img, self.selected_point)
            cv2.putText(display_img, "Click to select point, Enter to continue", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow(self.window_name, display_img)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                cv2.destroyAllWindows()
                return False
            elif key == 13:  # Enter
                cv2.destroyAllWindows()
                return True

    def ai_select(self,medicine_name) -> bool:
        """
        AI辅助选择点
        
        使用大模型自动识别图像中的药品并选择合适的抓取点
        
        Returns:
            bool: 是否成功选择点（True表示成功，False表示失败或用户取消）
        """
        try:
            self.logger.info("进入大模型自动选择模式")
            
            time.sleep(1)  # 等待相机稳定
            self.logger.info("正在获取图像...")
            color_img, _ = self.image_handler.get_images()
            if color_img is None:
                self.logger.error("无法获取图像")
                return False         
            
            self.logger.info(f"模型正在识别药品: {medicine_name}")
            # 将图像保存为临时JPG文件
            temp_img_path = tempfile.mktemp(suffix='.jpg')
            cv2.imwrite(temp_img_path, color_img)
            self.logger.info(f"图像已保存到临时文件: {temp_img_path}")
            
            time.sleep(1.5)
            # 使用图片路径进行识别
            image_input = ImageInput(image_path=temp_img_path)
            x, y = self.vision_api.detect_medicine_box(image_input, medicine_name)
            
            # 调试模式：不清理临时文件，方便查看保存的图片
            self.logger.info(f"调试模式：临时文件保留在 {temp_img_path}")
            # 清理临时文件（调试时注释掉）
            # try:
            #     os.remove(temp_img_path)
            #     self.logger.info("临时文件已清理")
            # except Exception as e:
            #     self.logger.warning(f"清理临时文件失败: {str(e)}")
            
            if x > 0 and y > 0:
                self.selected_point = [x, y]
                self.logger.info(f"成功识别药品 '{medicine_name}'，坐标: ({x}, {y})")
            else:
                self.logger.error(f"未能有效识别药品 '{medicine_name}'")
                return False
            
            # 显示选择结果
            display_img = self.image_handler.draw_point(color_img, self.selected_point)
            cv2.putText(display_img, "AI selected point, Press Enter to continue", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow(self.window_name, display_img)
            
            while True:
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    cv2.destroyAllWindows()
                    return False
                elif key == 13:  # Enter
                    cv2.destroyAllWindows()
                    return True
                    
        except Exception as e:
            self.logger.error(f"AI选择点时发生错误: {str(e)}")
            cv2.destroyAllWindows()
            return False
