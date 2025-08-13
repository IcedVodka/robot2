#!/usr/bin/env python3
import sys
import os
import logging
import cv2
import datetime

from Robot.sensor import depth_camera
from utils.logger import setup_logger, get_logger
from policy.segmentation import SamPredictor
import time
from Robot.sensor.depth_camera import RealsenseSensor
from Robot.sensor.rgb_camera import RgbCameraSensor
from Robot.robot.realman_controller import RealmanController
from grasp_task2.llm_quest import VisionAPI,ImageInput
from grasp_task2.config import grasp_config
from grasp_task2.vertical_catch import vertical_catch
from Robot.sensor.suction_sensor import SuctionController
from typing import Tuple, Optional
import numpy as np
from utils.others import get_images , mark_detected_medicine_on_image
from utils.others import print_grasp_poses
from Robot.sensor.lift import SerialLiftingMotor

def get_timestamped_path(filename):
    """
    生成带有时间戳的文件路径，保存到logs文件夹下
    
    Args:
        filename: 原始文件名
    
    Returns:
        带有时间戳的文件路径
    """
    # 确保logs文件夹存在
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 生成时间戳
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 构建新的文件名：时间戳_原始文件名
    new_filename = f"{timestamp}_{filename}"
    
    # 返回完整路径
    return os.path.join(logs_dir, new_filename)

class GraspTask:
    def __init__(self):
        self.logger = get_logger("GraspTask")
        self.config = grasp_config

        # 初始化各个模块
        self.llm_api = VisionAPI()
        # self.rgb_camera = RgbCameraSensor("rgb_camera")

        self.left_camera = RealsenseSensor("left_camera")     
        self.left_robot = RealmanController("left_robot",self.config.robots["left"])
        # self.left_suction = None
        
        self.right_camera = RealsenseSensor("right_camera")
        self.right_robot = RealmanController("right_robot",self.config.robots["right"])
        # self.right_suction = None

        self.lift = SerialLiftingMotor()
        self.lift.cmd_vel_callback(380)
        self.logger.info("移动升降机到380,开始sleep 10 秒")
        time.sleep(10)
    
        # SAM模型
        self.sam_model = None    

        # 临时变量
        # 药品列表
        self.medicine_list = []  

        self.right_moving_joints = [-84.74700164794922, 102.43099975585938, -131.4669952392578, -7.565999984741211, -62.077999114990234, 195.55599975585938]
        self.left_moving_joints = [85.58699798583984, 110.4489974975586, -119.98999786376953, 1.2890000343322754, -81.37899780273438, -183.7310028076172]


        self._init_components()
        
    def _init_components(self):
        """初始化所有组件"""
        try:
            self.sam_model = SamPredictor(self.config.sam_model_path)
            setup_logger()
            self.left_camera.set_up(self.config.cameras["left"].serial,self.config.cameras["left"].resolution)
            self.left_robot.set_up()
            self.left_robot.set_arm_joints_block([84.81500244140625, -47.86800003051758, -20.655000686645508, 2.125, -82.52300262451172, -183.72500610351562])
            self.left_robot.release_suck()
            
            self.right_camera.set_up(self.config.cameras["right"].serial,self.config.cameras["right"].resolution)         
            self.right_robot.set_up()
            self.right_robot.release_suck()
            self.right_robot.set_arm_joints_block(self.right_moving_joints)
            time.sleep(2)

            self.logger.info("所有组件初始化完成")
            return True
        except Exception as e:
            self.logger.error(f"组件初始化失败: {str(e)}")
            return False
    def cleanup(self):
        """清理资源"""
        self.logger.info("正在清理资源...")
        # if self.rgb_camera:
        #     self.rgb_camera.cleanup()
        if self.right_camera:
            self.right_camera.cleanup()
        if self.left_camera:
            self.left_camera.cleanup()
        # if self.right_suction:
        #     self.right_suction.close()  
        self.logger.info("资源清理完成")

    # 处方识别        
    def prescription_recognition(self):
        self.logger.info("开始处方识别")        
        self.medicine_list = []  

        try:
            bgr_frame = self.left_camera.get_information()['color']
            #保存图片
            img_path = get_timestamped_path("prescription.jpg")
            cv2.imwrite(img_path, bgr_frame)
            self.logger.info(f"处方图片保存成功: {img_path}")
            self.medicine_list  = self.llm_api.extract_prescription_medicines(ImageInput(image_np=bgr_frame))
            self.logger.info(f"识别到的药品: {self.medicine_list}")

        finally :
            if self.medicine_list is not None and len(self.medicine_list)!= 0 :
                self.left_robot.set_arm_joints_block(self.left_moving_joints)
        return self.medicine_list

    # 单个药品抓取
    def single_medicine_grasp(self, medicine_name, arm_side = "right" , use_sam = False):
        
        flag = False
        self.logger.info(f"single_medicine_grasp：开始抓取药品: {medicine_name}")

        # 获取对应的机械臂和相机
        robot = self.left_robot if arm_side == "left" else self.right_robot
        camera = self.left_camera if arm_side == "left" else self.right_camera
        camera_config = self.config.cameras["left"] if arm_side == "left" else self.config.cameras["right"]
        robot_config = self.config.robots["left"] if arm_side == "left" else self.config.robots["right"]

        robot.set_arm_init_joint()
        time.sleep(2)
        # 获取图像
        bgr_frame,depth_frame= get_images(camera, self.logger) 

        #保存图片
        img_path = get_timestamped_path(f"{arm_side}_rgb.jpg")
        cv2.imwrite(img_path, bgr_frame)
        self.logger.info(f"{arm_side} rgb图片保存成功: {img_path}")

        # 1. 识别药品
        # 只有两个退出条件，1. 识别成功然后抓取，不以是否抓取成功为条件 2. 识别失败
        bbox = self.llm_api.detect_medicine_box(ImageInput(image_path=img_path), medicine_name)
        self.logger.info(f"识别到的药品边界框: {bbox}")
        if bbox[0] <= 0 or bbox[1] <= 0 or bbox[2] <= 0 or bbox[3] <= 0:
            self.logger.error(f"未能有效识别药品 '{medicine_name}'")
            return False

        x1, y1, x2, y2 = bbox
        self.logger.info(f"成功识别药品 '{medicine_name}'，边界框: ({x1}, {y1}, {x2}, {y2})")
        
        try:
            # 计算中心点坐标用于深度值获取
            x = (x1 + x2) // 2
            y = (y1 + y2) // 2
            depth_value = depth_frame[y, x]
            self.logger.info(f"首次获取到的深度值: {depth_value}")
        except:
            self.logger.error(f"未能获取到有效深度值")
            return False
        
        # 确保获取到有效的深度值，最多尝试200次
        attempt_count = 0
        max_attempts = 200
        while depth_value <= 0 and attempt_count < max_attempts:
            bgr_frame, depth_frame = get_images(camera, self.logger)
            depth_value = depth_frame[y, x]
            time.sleep(0.3)
            attempt_count += 1
            
        if depth_value <= 0:
            self.logger.error(f"无法获取药品 '{medicine_name}' 的有效深度信息，已尝试 {max_attempts} 次")
            return False

        self.logger.info(f"最终获取到的深度值: {depth_value}")
        
        # 保存标记了识别位置的图片
        marked_image_path = get_timestamped_path(f"{arm_side}_detected_medicine.jpg")
        mark_detected_medicine_on_image(bgr_frame, bbox, depth_value, medicine_name, marked_image_path)
        self.logger.info(f"药品识别边界框标记图片保存成功: {marked_image_path}")

        mask = None
        # 2. Sam分割
        if use_sam:
            rgb_image = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            center, mask = self.sam_model.predict(rgb_image, bboxes=bbox)
            self.logger.info(f"Sam分割成功")
            #保存图片
            img_path = get_timestamped_path(f"{arm_side}_sam_mask.jpg")
            cv2.imwrite(img_path, mask)
            self.logger.info(f"Sam分割结果保存成功: {img_path}")
        else:
            self.logger.info(f"未使用Sam分割")

        # 3. 计算抓取姿态
        pose = robot.get_state()["pose"]      
        computed_object_pose, prepared_angle_pose, finally_pose = vertical_catch(
            mask=mask,
            depth_frame=depth_frame,
            color_intr=camera_config.color_intr,
            current_pose=pose,
            adjustment=robot_config.adjustment,
            rotation_matrix=camera_config.rotation_matrix,
            translation_vector=camera_config.translation_vector,
            x = x,
            y = y,
        )      

        if arm_side == "right":
            prepared_angle_pose[3:] = [-1.564, 0, 3.141]
            finally_pose[3:] = [-1.564, 0, 3.141]
        else:
            prepared_angle_pose[3:] = [1.571, 0.524, 3.142]
            finally_pose[3:] = [1.571, 0.524, 3.142]

         
        print_grasp_poses(computed_object_pose, prepared_angle_pose, finally_pose ,logger=self.logger)

        robot.suck()

        try:
            # 4. 抓取药品            
            self.logger.info(f"开始移动到prepared_angle_pose{prepared_angle_pose}")
            robot.set_pose_block(prepared_angle_pose, linear=False)
            time.sleep(1.5)
            self.logger.info(f"开始移动到finally_pose{finally_pose}")    
            robot.set_pose_block(finally_pose, linear=True)
            time.sleep(1.5)
            finally_pose[2] = finally_pose[2] +0.02
            self.logger.info(f"开始移动到finally_pose往上抬2cm的位置{finally_pose}")    
            robot.set_pose_block(finally_pose, linear=True)
            time.sleep(1.5)
            prepared_angle_pose[2] = prepared_angle_pose[2] +0.02
            if arm_side == "right":
                prepared_angle_pose[1] = prepared_angle_pose[1] +0.03
            else:
                prepared_angle_pose[1] = prepared_angle_pose[1] -0.03
            self.logger.info(f"开始移动到prepared_angle_pose往上抬2cm,往后抬3cm的位置{prepared_angle_pose}")
            robot.set_pose_block(prepared_angle_pose, linear=True)
            time.sleep(1.5)
            self.logger.info(f"药品抓取成功: {medicine_name}")  
            flag = True
        except:
            self.logger.error(f"药品抓取失败: {medicine_name}")
        finally :
            self.logger.info(f"开始移动到mov")
            if arm_side == "right":
                robot.set_arm_joints_block(self.right_moving_joints)
            else:
                robot.set_arm_joints_block(self.left_moving_joints)
            time.sleep(2)
            self.logger.info(f"开始移动到放取预备位姿")
            robot.set_arm_fang_joint()
            time.sleep(1.5)
            self.logger.info(f"开始释放 suction")
            robot.release_suck()
            time.sleep(2)
            if arm_side == "right":
                robot.set_arm_joints_block(self.right_moving_joints)
            else:
                robot.set_arm_joints_block(self.left_moving_joints)
            self.logger.info(f"复位姿态成功")
            return flag
    
    # 抓取一层药品
    def layer_grasp(self):
        self.logger.info(f"layer_grasp：开始抓取一层药品，当前药品列表: {self.medicine_list}")
        
        if self.medicine_list is None or len(self.medicine_list) == 0:
            self.logger.info("layer_grasp：没有药品可以抓取,直接返回")
            return 
        
        medicines = self.medicine_list.copy()        
        # 遍历尝试抓取每个药品
        for i, medicine in enumerate(medicines):
            if self.single_medicine_grasp(medicine, arm_side="right"):
                # 抓取成功，标记为None
                medicines[i] = None
            else:
                self.logger.warning(f"右臂：药品 '{medicine}' 抓取失败")        
        # 更新medicine_list，只保留未抓取成功的药品
        self.medicine_list = [m for m in medicines if m is not None]
        self.logger.info(f"右臂抓取完毕，开始左臂抓取，当前药品列表: {self.medicine_list}")



        if self.medicine_list is None or len(self.medicine_list) == 0:
            self.logger.info("layer_grasp：没有药品可以抓取,直接返回")
            return 
        
        medicines = self.medicine_list.copy()
        for i, medicine in enumerate(self.medicine_list):
            if self.single_medicine_grasp(medicine, arm_side="left"):
                # 抓取成功，标记为None
                medicines[i] = None
            else:
                self.logger.warning(f"左臂：药品 '{medicine}' 抓取失败")        
        # 更新medicine_list，只保留未抓取成功的药品
        self.medicine_list = [m for m in medicines if m is not None]
        self.logger.info(f"左臂抓取完毕，剩余药品: {self.medicine_list}")

        return 
    
    # 抓取一个货架多层药品
    def shelf_grasp(self):
        self.logger.info(f"shelf_grasp：开始抓取一个货架多层药品，当前药品列表: {self.medicine_list}")
        if self.medicine_list is None or len(self.medicine_list) == 0:
            self.logger.info("shelf_grasp：没有药品可以抓取,直接返回")
            return 
        
        self.lift.cmd_vel_callback(300)
        self.logger.info("移动升降机到300,开始sleep 15 秒")
        time.sleep(10)
        self.layer_grasp()

        self.lift.cmd_vel_callback(0)
        self.logger.info("移动升降机到0,开始sleep 15 秒")
        time.sleep(15)
        self.layer_grasp()

        self.lift.cmd_vel_callback(380)
        self.logger.info("移动升降机到380,开始sleep 15 秒")
        time.sleep(15)

    
    # 放置药品篮子
    def place_medicine_basket(self):
        
        self.logger.info("开始放置药品篮子")
        self.medicine_list = [] 

        l = [88.4, -31.496, -106.685, 5.506, -55.987,-184.599]
        r = [-84.745, -26.176, -111.336, -1.509, -51.940, 195.556]

        self.left_robot.suck()
        self.right_robot.suck()
        self.left_robot.robot.rm_movej(joint = l ,v = 15 ,r = 0,connect=0,block= 0)
        self.right_robot.robot.rm_movej(joint = r ,v = 15,r = 0,connect=0,block= 0)
        self.logger.info("移动到预备位置")     
        time.sleep(7)


        r = [18.198/1000, -230.454/1000,173.369/1000,-3.080,-0.154,1.404]
        l = [-4.777/1000,239.159/1000,163.029/1000,3.055,-0.243,-1.572]
        r[2] = r[2] - 0.015
        l[2] = l[2] - 0.015
        self.left_robot.robot.rm_movel(pose = l ,v = 15,r = 0,connect=0,block= 0)
        self.right_robot.robot.rm_movel(pose = r ,v = 15,r = 0,connect=0,block= 0)
        self.logger.info("下降1.5cm")
        time.sleep(15)

        
        r[2] = r[2] + 0.10
        l[2] = l[2] + 0.10        
        self.left_robot.robot.rm_movel(pose = l ,v = 15,r = 0,connect=0,block= 0)
        self.right_robot.robot.rm_movel(pose = r ,v = 15,r = 0,connect=0,block= 0)
        self.logger.info("上升10cm")
        time.sleep(15)

        l[1] = l[1] + 0.14
        r[1] = r[1] - 0.14
        self.left_robot.robot.rm_movel(pose = l ,v = 15,r = 0,connect=0,block= 0)
        self.right_robot.robot.rm_movel(pose = r ,v = 15,r = 0,connect=0,block= 0)
        self.logger.info("向前14cm")
        time.sleep(20)

        self.left_robot.release_suck()
        self.right_robot.release_suck()
        time.sleep(2)

        
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
       






 