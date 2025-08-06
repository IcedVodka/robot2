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

import cv2


class GraspTask:
    def __init__(self):
        self.logger = get_logger("GraspTask")
        self.config = grasp_config

        # 初始化各个模块
        self.llm_api = VisionAPI()
        self.left_camera = RealsenseSensor("left_camera")
        self.right_camera = RealsenseSensor("right_camera")
        self.rgb_camera = RgbCameraSensor("rgb_camera")
        self.left_robot = RealmanController("left_robot")
        self.right_robot = RealmanController("right_robot")
    
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
            self.left_camera.set_up(self.config.cameras.left.serial)
            self.right_camera.set_up(self.config.cameras.right.serial)
            self.rgb_camera.set_up(self.config.rgb_camera_id)
            self.left_robot.set_up(self.config.robots.left.ip, self.config.robots.left.port)
            self.right_robot.set_up(self.config.robots.right.ip, self.config.robots.right.port)
            time.sleep(2)
            self.logger.info("所有组件初始化完成")
            return True
        except Exception as e:
            self.logger.error(f"组件初始化失败: {str(e)}")
            return False

    # 处方识别        
    def prescription_recognition(self):
        self.logger.info("开始处方识别")
        bgr_frame = self.rgb_camera.get()['color']
        #保存图片
        cv2.imwrite("prescription.jpg", bgr_frame)
        self.logger.info("处方图片保存成功")
        return self.llm_api.extract_prescription_medicines(ImageInput(image_np=bgr_frame))

    # 单个药品抓取
    def single_medicine_grasp(self, medicine_name, arm_side = "right" , use_sam = True):
        self.logger.info(f"开始抓取药品: {medicine_name}")

        # 获取对应的机械臂和相机
        robot = self.left_robot if arm_side == "left" else self.right_robot
        camera = self.left_camera if arm_side == "left" else self.right_camera
        camera_config = self.config.cameras.left if arm_side == "left" else self.config.cameras.right
        robot_config = self.config.robots.left if arm_side == "left" else self.config.robots.right

        # 获取图像
        data = camera.get()
        bgr_frame = data["color"].copy()
        depth_frame = data["depth"].copy()
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

        # 2. Sam分割
        if use_sam:
            rgb_image = cv2.cvtColor(self.image_handler.last_color_image, cv2.COLOR_BGR2RGB)
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
        
        return True

 