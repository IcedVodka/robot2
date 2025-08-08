#!/usr/bin/env python3

import sys
import os
import logging


from Robot.sensor import depth_camera
from utils.logger import setup_logger, get_logger
from policy.segmentation import SamPredictor
import time
from Robot.sensor.depth_camera import RealsenseSensor
from Robot.sensor.rgb_camera import RgbCameraSensor
from Robot.robot.realman_controller import RealmanController
from grasp_task2.llm_quest import VisionAPI,ImageInput
from grasp_task2.config import grasp_config
from utils.vertical_grab.interface import vertical_catch
from Robot.sensor.suction_sensor import SuctionController
from typing import Tuple, Optional
import numpy as np
import cv2

def get_images(sensor, logger) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """获取彩色和深度图像"""
        try:
            data = sensor.get_information()
            if data and "color" in data and "depth" in data:
                last_color_image = data["color"].copy()
                last_depth_image = data["depth"].copy()
                return last_color_image, last_depth_image
            return None, None
        except Exception as e:
            logger.error(f"获取图像失败: {str(e)}")
            return None, None

def mark_detected_medicine_on_image(image: np.ndarray, x: int, y: int, depth: float, 
                                  medicine_name: str, output_path: str) -> None:
    """
    在图片上标记识别到的药品位置并保存
    
    Args:
        image: 原始图片 (BGR格式)
        x: 识别到的x坐标
        y: 识别到的y坐标  
        depth: 该点的深度值
        medicine_name: 药品名称
        output_path: 输出图片路径
    """
    # 复制图片避免修改原图
    marked_image = image.copy()
    
    # 绘制圆圈标记识别位置
    cv2.circle(marked_image, (x, y), 10, (0, 255, 0), 2)  # 绿色圆圈
    
    # 绘制十字线
    cv2.line(marked_image, (x-15, y), (x+15, y), (0, 255, 0), 2)  # 水平线
    cv2.line(marked_image, (x, y-15), (x, y+15), (0, 255, 0), 2)  # 垂直线
    
    # 准备文本信息
    text_info = f"Medicine: {medicine_name}"
    coord_info = f"Position: ({x}, {y})"
    depth_info = f"Depth: {depth:.3f}m"
    
    # 设置文本参数
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    color = (0, 255, 0)  # 绿色
    
    # 计算文本位置
    text_y_start = 30
    line_height = 25
    
    # 绘制文本
    cv2.putText(marked_image, text_info, (10, text_y_start), font, font_scale, color, thickness)
    cv2.putText(marked_image, coord_info, (10, text_y_start + line_height), font, font_scale, color, thickness)
    cv2.putText(marked_image, depth_info, (10, text_y_start + 2*line_height), font, font_scale, color, thickness)
    
    # 保存图片
    cv2.imwrite(output_path, marked_image)

class GraspTask:
    def __init__(self):
        self.logger = get_logger("GraspTask")
        self.config = grasp_config

        # 初始化各个模块
        self.llm_api = VisionAPI()
        self.rgb_camera = RgbCameraSensor("rgb_camera")

        self.left_camera = None     
        self.left_robot = None
        self.left_suction = None
        
        self.right_camera = RealsenseSensor("right_camera")
        self.right_robot = RealmanController("right_robot")
        self.right_suction = SuctionController()
        
    
        # SAM模型
        self.sam_model = None    

        # 临时变量
        # 药品列表
        self.medicine_list = []  


        self._init_components()
        
    def _init_components(self):
        """初始化所有组件"""
        try:
            self.sam_model = SamPredictor(self.config.sam_model_path)
            self.rgb_camera.set_up(self.config.rgb_camera_id)

            # self.left_camera.set_up(self.config.cameras.left.serial)
            # self.left_robot.set_up(self.config.robots.left.ip, self.config.robots.left.port)

            self.right_camera.set_up(self.config.cameras["right"].serial)         
            self.right_robot.set_up(self.config.robots["right"].ip, self.config.robots["right"].port)
            time.sleep(2)
            self.logger.info("所有组件初始化完成")
            return True
        except Exception as e:
            self.logger.error(f"组件初始化失败: {str(e)}")
            return False
    def cleanup(self):
        """清理资源"""
        self.logger.info("正在清理资源...")
        if self.rgb_camera:
            self.rgb_camera.cleanup()
        if self.right_camera:
            self.right_camera.cleanup()
        if self.right_suction:
            self.right_suction.close()  
        self.logger.info("资源清理完成")

    # 处方识别        
    def prescription_recognition(self):
        self.logger.info("开始处方识别")
        bgr_frame = self.rgb_camera.get()['color']
        #保存图片
        cv2.imwrite("prescription.jpg", bgr_frame)
        self.logger.info("处方图片保存成功")
        self.medicine_list  = self.llm_api.extract_prescription_medicines(ImageInput(image_np=bgr_frame))
        return self.medicine_list

    # 单个药品抓取
    def single_medicine_grasp(self, medicine_name, arm_side = "right" , use_sam = True):
        self.logger.info(f"开始抓取药品: {medicine_name}")

        # 获取对应的机械臂和相机
        robot = self.left_robot if arm_side == "left" else self.right_robot
        camera = self.left_camera if arm_side == "left" else self.right_camera
        camera_config = self.config.cameras["left"] if arm_side == "left" else self.config.cameras["right"]
        robot_config = self.config.robots["left"] if arm_side == "left" else self.config.robots["right"]
        suction = self.left_suction if arm_side == "left" else self.right_suction

    
        # 获取图像
        bgr_frame,depth_frame= get_images(camera, self.logger) 

        # 保存图片
        cv2.imwrite(f"{arm_side}_before_grasp.jpg", bgr_frame)
        self.logger.info(f"药品抓取前图片保存成功: {arm_side}_before_grasp.jpg")

        # 1. 识别药品
        # 只有两个退出条件，1. 识别成功然后抓取，不以是否抓取成功为条件 2. 识别失败
        x, y = self.llm_api.detect_medicine_box(ImageInput(image_np=bgr_frame), medicine_name)
        if x <= 0 or y <= 0:
            self.logger.error(f"未能有效识别药品 '{medicine_name}'")
            return False

        self.logger.info(f"成功识别药品 '{medicine_name}'，坐标: ({x}, {y})")
        
        # 获取该点的深度信息
        depth_value = depth_frame[y, x] if depth_frame is not None else 0.0
        
        # 保存标记了识别位置的图片
        marked_image_path = f"{arm_side}_detected_medicine.jpg"
        mark_detected_medicine_on_image(bgr_frame, x, y, depth_value, medicine_name, marked_image_path)
        self.logger.info(f"药品识别位置标记图片保存成功: {marked_image_path}")

        # 2. Sam分割
        if use_sam:
            rgb_image = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            center, mask = self.sam_model.predict(rgb_image, points=[x,y])    
            self.logger.info(f"Sam分割成功")
            #保存图片
            cv2.imwrite(f"{arm_side}_sam_mask.jpg", mask)
            self.logger.info(f"Sam分割结果保存成功: {arm_side}_sam_mask.jpg")
        else:
            self.logger.info(f"未使用Sam分割")

        # 3. 计算抓取姿态
        pose = robot.get_state()["pose"]        
        self.logger.info(f"当前{arm_side}机械臂姿态: {pose}")
        computed_object_pose, prepared_angle_pose, finally_pose = vertical_catch(
            mask=mask,
            depth_frame=depth_frame,
            color_intr=camera_config.color_intr,
            current_pose=pose,
            adjustment=robot_config.adjustment,
            vertical_rx_ry_rz=None,
            rotation_matrix=camera_config.rotation_matrix,
            translation_vector=camera_config.translation_vector,
            use_point_depth_or_mean=True
        )

        # 4. 抓取药品
        suction.suck()
        robot.set_pose_block(prepared_angle_pose, linear=False)
        time.sleep(2)
        robot.set_pose_block(finally_pose, linear=True)
        time.sleep(2)
        robot.set_pose_block(prepared_angle_pose, linear=True)
        time.sleep(1.5)
        robot.set_arm_init_joint()
        time.sleep(1.5)
        robot.set_arm_fang_joint()
        time.sleep(1.5)
        suction.release()
        time.sleep(2)
        robot.set_arm_init_joint()
        self.logger.info(f"药品抓取成功: {medicine_name}")
        return True
    
    # 抓取一层药品
    def layer_grasp(self):
        medicines = self.medicine_list.copy()
        
        # 遍历尝试抓取每个药品
        for i, medicine in enumerate(medicines):
            if self.single_medicine_grasp(medicine, arm_side="right"):
                # 抓取成功，标记为None
                medicines[i] = None
            else:
                self.logger.warning(f"药品 '{medicine}' 抓取失败")
        
        # 更新medicine_list，只保留未抓取成功的药品
        self.medicine_list = [m for m in medicines if m is not None]
        self.logger.info(f"抓取一层药品完成，剩余药品: {self.medicine_list}")
        return True
    
    # 抓取一个货架多层药品
    def shelf_grasp(self):
        pass
    
    def run(self):
        setup_logger()
        try:
            self.medicine_list = self.prescription_recognition()
            self.logger.info(f"处方识别完成，药品列表: {self.medicine_list}")
            self.layer_grasp()
        finally :
            self.cleanup()
       
if __name__ == "__main__":
    grasp_task = GraspTask()
    grasp_task.run()
       






 