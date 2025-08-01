#!/usr/bin/env python3

import cv2
import numpy as np
from typing import List, Optional
from utils.llm_quest import detect_medicine_box

class PointSelector:
    def __init__(self, image_handler, logger):
        self.image_handler = image_handler
        self.logger = logger
        self.selected_point = [320, 240]  # 默认中心点
        self.window_name = "Point Selection"

    def mouse_callback(self, event, x, y, flags, param):
        """鼠标回调函数"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.selected_point = [x, y]
            self.logger.info(f"用户选择点: ({x}, {y})")

    def manual_select(self) -> bool:
        """手动选择点"""
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

    def ai_select(self) -> bool:
        """AI选择点"""
        self.logger.info("进入大模型自动选择模式")
        
        color_img, _ = self.image_handler.get_images()
        if color_img is None:
            self.logger.error("无法获取图像")
            return False
        
        # 保存图片到临时文件用于AI处理
        temp_image_path = "/tmp/current_image.jpg"
        cv2.imwrite(temp_image_path, color_img)
        
        # 获取用户输入的药品名称
        print("\n请输入要识别的药品名称:")
        medicine_name = input().strip()
        
        if not medicine_name:
            self.logger.warning("未输入药品名称，使用默认中心点")
            return True
        
        self.logger.info(f"正在识别药品: {medicine_name}")
        coordinates = detect_medicine_box(temp_image_path, medicine_name)
        
        if coordinates and coordinates != [0, 0]:
            self.selected_point = coordinates
            self.logger.info(f"成功识别药品 '{medicine_name}'，坐标: {coordinates}")
        else:
            self.logger.warning(f"未找到药品 '{medicine_name}'，使用默认中心点")
            self.selected_point = [320, 240]
        
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
