#!/usr/bin/env python3
"""
机械臂抓取程序 - 简化版本

阶段1: 从RealsenseSensor获取彩色和深度图像，通过OpenCV窗口展示
       用户可以选择一个点（默认中心），按回车进入下一阶段

阶段2: 基于用户选择的点和深度图像，使用SAM模型进行推理
       展示mask图像，按回车进入下一阶段

阶段3: 机械臂执行抓取动作，按回车进入下一阶段

阶段4: 机械臂复位，按回车回到阶段1

按ESC退出程序
"""

import cv2
import numpy as np
import time
import sys
import os
import logging
from typing import Tuple, Optional, Dict, Any
from utils.logger import setup_logger, get_logger
from Robot.sensor.suction_sensor import SuctionController

# 添加项目路径
sys.path.append(os.path.abspath('.'))

from Robot.sensor.depth_camera import RealsenseSensor
from policy.segmentation import SamPredictor
from Robot.robot.realman_controller import RealmanController
from utils.logger import get_logger
from utils.vertical_grab.interface import vertical_catch
from utils.others import print_grasp_poses

class GraspController:
    """机械臂抓取控制器"""
    
    def __init__(self):
        """初始化控制器"""
        self.logger = get_logger("GraspController")
                       
        # 初始化组件
        self.sensor = None
        self.robot = None
        self.sam_model = None
        self.suction = None
        
        # 状态变量
        self.selected_point = [320, 240]
        self.last_depth_image = None
        self.last_color_image = None
        self.mask_result = None
        self.grasp_pose = None
              
        # 窗口名称
        self.window_name = "Grasp Control"

        # 相机参数
        self.camera_serial = "327122072195"        
        # 相机标定参数
        self.rotation_matrix = [
            [0.01063683, 0.99986326, -0.01266192],
            [-0.99992363, 0.01055608, -0.00642741],
            [-0.00629287, 0.01272932, 0.99989918]
        ]        
        self.translation_vector = [-0.09011056,  0.02759339,  0.02540262] 
        self.color_intr = {
            'ppx': 329.98211669921875,
            'ppy': 246.95748901367188,
            'fx': 607.5119018554688,
            'fy': 607.0875854492188
        }

        # 机械臂参数
        self.arm_move_speed = 20
        self.robot_ip = "192.168.1.18"
        self.robot_port = 8080


        # 平面抓取参数
        self.adjustment = [0.1, 0.05] #安全预备位置在计算位置的基础上向后调整0m，最终抓取位置在计算位置的基础上向前调整0.025m

        self._init_components()

    def _init_components(self):
        self.sam_model = SamPredictor("/home/gml-cwl/code/robot2/assets/weights/sam_b.pt")

        self.sensor = RealsenseSensor("hand_camera")
        self.sensor.set_up(camera_serial=self.camera_serial, is_depth=True)
        
        self.robot = RealmanController("grasp_robot")
        self.robot.set_up(self.robot_ip, self.robot_port)
        self.robot.set_arm_init_joint()

        self.suction = SuctionController()

        self.logger.info("所有组件初始化完成")
        return True        
    
    def mouse_callback(self, event, x, y, flags, param):
        """鼠标回调函数，处理点选择"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.selected_point = [x, y]
            self.logger.info(f"用户选择点: ({x}, {y})")
    
    def get_images(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """获取彩色和深度图像"""
        try:
            data = self.sensor.get_information()
            if data and "color" in data and "depth" in data:
                return data["color"], data["depth"]
            return None, None
        except Exception as e:
            self.logger.error(f"获取图像失败: {str(e)}")
            return None, None
    
    def draw_selected_point(self, image: np.ndarray) -> np.ndarray:
        """在图像上绘制选择的点"""
        if self.selected_point:
            x, y = self.selected_point
            cv2.circle(image, (x, y), 6, (0, 255, 0), 2)
            cv2.circle(image, (x, y), 1, (0, 255, 0), -1)
            
            # 显示坐标信息
            coord_text = f"({x}, {y})"
            cv2.putText(image, coord_text, (x+15, y-15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # 显示深度信息
            if self.last_depth_image is not None and 0 <= x < self.last_depth_image.shape[1] and 0 <= y < self.last_depth_image.shape[0]:
                depth_value = self.last_depth_image[y, x]
                depth_cm = depth_value / 10.0  # 转换为厘米
                depth_text = f"Depth: {depth_cm:.1f}cm"
                cv2.putText(image, depth_text, (x+15, y+5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        return image
    
    def stage1_image_selection(self):
        """阶段1: 图像展示和点选择"""
        self.logger.info("=== 阶段1: 图像展示和点选择 ===")
        self.logger.info("点击选择目标点，默认中心点，回车进入下一阶段, ESC退出程序")

        # 先创建窗口，然后设置鼠标回调
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        while True:
            # 获取图像
            color_img, depth_img = self.get_images()
            if color_img is None:
                self.logger.warning("无法获取图像，重试中...")
                time.sleep(0.1)
                continue
            
            # 保存最后的图像用于后续处理
            self.last_color_image = color_img.copy()
            self.last_depth_image = depth_img.copy()
            
            # 显示彩色图像
            display_img = color_img.copy()
            display_img = self.draw_selected_point(display_img)
            
            # 添加说明文字
            cv2.putText(display_img, "Click to select point, Enter to continue", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)            
            cv2.imshow(self.window_name, display_img)
            
            # 处理按键
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                return False
            elif key == 13:  # Enter                
                break
        
        cv2.destroyAllWindows()
        return True
    
    def stage2_sam_segmentation(self):
        """阶段2: SAM分割推理"""
        self.logger.info("=== 阶段2: SAM分割推理 ===")
        self.logger.info("正在使用SAM模型进行分割...")
        
        if self.last_color_image is None or self.selected_point is None:
            self.logger.error("缺少必要的图像数据或选择点")
            return False
        
        try:
            # 将BGR图像转换为RGB格式
            rgb_image = cv2.cvtColor(self.last_color_image, cv2.COLOR_BGR2RGB)
            
            # 使用SAM进行分割
            center, mask = self.sam_model.predict(rgb_image, points=self.selected_point)
            
            if mask is not None:
                self.mask_result = mask
                self.logger.info(f"SAM分割成功，中心点: {center}")
                
                # 显示分割结果
                cv2.imshow("SAM Segmentation Result", mask)

                # 计算抓取位置
                self.calculate_grasp_position()
                self.logger.info("抓取位置计算完成")                

                self.logger.info("分割结果已显示，在屏幕按任意键继续...")                
                cv2.waitKey(0)
                cv2.destroyAllWindows()




                return True
            else:
                self.logger.warning("SAM分割失败，未得到有效掩码")
                return False
                
        except Exception as e:
            self.logger.error(f"SAM分割失败: {str(e)}")
            return False
    
    def calculate_grasp_position(self) :
        state = self.robot.get_state()
        pose = state["pose"]

        self.logger.info(f"当前机械臂姿态: {pose}")

        computed_object_pose, prepared_angle_pose, finally_pose = vertical_catch(
            mask=self.mask_result,
            depth_frame=self.last_depth_image,
            color_intr=self.color_intr,
            current_pose=pose,
            adjustment=self.adjustment,
            vertical_rx_ry_rz=None,
            rotation_matrix=self.rotation_matrix,
            translation_vector=self.translation_vector,
            use_point_depth_or_mean=True
        )

        self.grasp_pose = (computed_object_pose, prepared_angle_pose, finally_pose)

        print_grasp_poses(self.grasp_pose[0], self.grasp_pose[1], self.grasp_pose[2],self.logger)
    
    def stage3_robot_grasp(self):
        """阶段3: 机械臂抓取"""
        self.logger.info("=== 阶段3: 机械臂抓取 ===")
        self.logger.info("正在执行抓取动作...")

        #用户输入y/n，y则执行抓取，n则不执行
        # user_input = input("请输入y/n: ")
        # if user_input == "y":
        self.suction.suck()
        self.robot.set_pose_block(self.grasp_pose[1],linear=False)
        time.sleep(2)
        self.robot.set_pose_block(self.grasp_pose[2],linear=True)
        time.sleep(2)
        # else:
        #     self.logger.info("用户选择不执行抓取")
        #     return False
        
        # 等待用户按回车继续
        # input("按回车键进入下一阶段...")        
        return True
    
    def stage4_robot_reset(self):
        """阶段4: 机械臂复位"""
        self.logger.info("=== 阶段4: 机械臂复位 ===")
        self.logger.info("正在复位机械臂...")
        self.robot.set_pose_block(self.grasp_pose[1],linear=True)
        time.sleep(1.5)
        self.robot.set_arm_init_joint() 
        time.sleep(1.5)       
        # input("按回车键移动到放置位置...")
        self.robot.set_arm_fang_joint()
        time.sleep(1.5)
        # input("按回车键松开吸盘并移动到初始位置...")
        self.suction.release()
        self.robot.set_arm_init_joint()
        time.sleep(1)
        return True
    
    def run(self):
        """主运行循环"""
       
        self.logger.info("机械臂抓取程序启动")
        self.logger.info("=== 机械臂抓取程序 ===")
        self.logger.info("程序将按以下阶段运行:")
        self.logger.info("阶段1: 图像展示和点选择")
        self.logger.info("阶段2: SAM分割推理")
        self.logger.info("阶段3: 机械臂抓取")
        self.logger.info("阶段4: 机械臂复位")
        self.logger.info("按ESC退出程序")
        self.logger.info("")
        
        try:
            while True:
                # 阶段1: 图像展示和点选择
                if not self.stage1_image_selection():
                    break
                
                # 阶段2: SAM分割推理
                if not self.stage2_sam_segmentation():
                    self.logger.warning("SAM分割失败，重新开始...")
                    continue
                
                # 阶段3: 机械臂抓取
                if not self.stage3_robot_grasp():
                    self.logger.warning("抓取失败，重新开始...")
                    continue
                
                # 阶段4: 机械臂复位
                if not self.stage4_robot_reset():
                    self.logger.warning("复位失败，重新开始...")
                    continue
                
                self.logger.info("一个完整周期完成，准备开始下一轮...")
                input("按回车键开始下一轮...")
                
        except KeyboardInterrupt:
            self.logger.info("用户中断程序")
        except Exception as e:
            self.logger.error(f"程序运行异常: {str(e)}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        self.logger.info("正在清理资源...")
        
        if self.sensor:
            self.sensor.cleanup()
        
        cv2.destroyAllWindows()
        
        self.logger.info("资源清理完成")

def main():
    """主函数"""
    setup_logger(log_level=logging.DEBUG, enable_color=True)
    controller = GraspController()
    controller.run()

if __name__ == "__main__":
    main()
