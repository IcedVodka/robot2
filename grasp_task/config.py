#!/usr/bin/env python3

from typing import Optional, Dict
import numpy as np
from Robot.sensor.depth_camera import RealsenseSensor

class GraspConfig:
    def __init__(self):
        # 相机参数
        self.camera_serial = "327122072195"
        
        # 相机标定参数 - 默认值，可以通过update_camera_params更新
        self.rotation_matrix = [
            [0.01063683, 0.99986326, -0.01266192],
            [-0.99992363, 0.01055608, -0.00642741],
            [-0.00629287, 0.01272932, 0.99989918]
        ]
        self.translation_vector = [-0.09011056, 0.02759339, 0.02540262]
        self.color_intr = {
            'ppx': 329.98211669921875,
            'ppy': 246.95748901367188,
            'fx': 607.5119018554688,
            'fy': 607.0875854492188
        }
        # 机械臂参数
        self.robot_ip = "192.168.1.18"
        self.robot_port = 8080
                
        # 平面抓取参数
        self.adjustment = [0.1, 0.03]  # 安全预备位置和最终抓取位置的调整参数

        # 处方rgb相机参数
        self.rgb_camera_id = 6

        # 其他配置参数
        self.sam_model_path = "/home/gml-cwl/code/robot2/assets/weights/sam_l.pt"        
   
