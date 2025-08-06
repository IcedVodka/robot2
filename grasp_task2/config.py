#!/usr/bin/env python3

from typing import Optional, Dict, Literal
import numpy as np
import yaml
import os
from dataclasses import dataclass, asdict
from Robot.sensor.depth_camera import RealsenseSensor

@dataclass
class CameraParams:
    """相机参数类"""
    serial: str
    rotation_matrix: list
    translation_vector: list
    color_intr: Dict[str, float]
    
@dataclass 
class RobotParams:
    """机械臂参数类"""
    ip: str
    port: int
    adjustment: list  # [安全预备位置偏移, 最终抓取位置偏移]

class GraspConfig:
    def __init__(self):
        # 相机配置 - 左、中、右三个相机
        self.cameras = {
            'left': CameraParams(
                serial="327122072195",  # 左相机序列号
                rotation_matrix=[
                    [0.01063683, 0.99986326, -0.01266192],
                    [-0.99992363, 0.01055608, -0.00642741],
                    [-0.00629287, 0.01272932, 0.99989918]
                ],
                translation_vector=[-0.09011056, 0.02759339, 0.02540262],
                color_intr={
                    'ppx': 329.98211669921875,
                    'ppy': 246.95748901367188,
                    'fx': 607.5119018554688,
                    'fy': 607.0875854492188
                }
            ),
            'center': CameraParams(
                serial="207522073950",  # 中央相机序列号
                rotation_matrix=[
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0]
                ],
                translation_vector=[0.0, 0.0, 0.0],
                color_intr={
                    'ppx': 320.0,
                    'ppy': 240.0,
                    'fx': 600.0,
                    'fy': 600.0
                }
            ),
            'right': CameraParams(
                serial="000000000000",  # 右相机序列号（待配置）
                rotation_matrix=[
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0]
                ],
                translation_vector=[0.0, 0.0, 0.0],
                color_intr={
                    'ppx': 320.0,
                    'ppy': 240.0,
                    'fx': 600.0,
                    'fy': 600.0
                }
            )
        }
        
        # 机械臂配置 - 左、右两个机械臂
        self.robots = {
            'left': RobotParams(
                ip="192.168.1.18",
                port=8080,
                adjustment=[0.1, 0.03]  # [安全预备位置偏移, 最终抓取位置偏移]
            ),
            'right': RobotParams(
                ip="192.168.1.19",  # 右机械臂IP（待配置）
                port=8080,
                adjustment=[0.1, 0.03]
            )
        }
        
        # RGB相机参数（处方识别用）
        self.rgb_camera_id = 6
        
        # 其他配置参数
        self.sam_model_path = "/home/gml-cwl/code/robot2/assets/weights/sam_l.pt"
    
    def get_camera_params(self, position: Literal['left', 'center', 'right']) -> CameraParams:
        """获取指定位置的相机参数"""
        return self.cameras[position]
    
    def get_robot_params(self, position: Literal['left', 'right']) -> RobotParams:
        """获取指定位置的机械臂参数"""
        return self.robots[position]
    
    def update_camera_params(self, position: Literal['left', 'center', 'right'], **kwargs):
        """更新相机参数"""
        camera = self.cameras[position]
        for key, value in kwargs.items():
            if hasattr(camera, key):
                setattr(camera, key, value)
    
    def update_robot_params(self, position: Literal['left', 'right'], **kwargs):
        """更新机械臂参数"""
        robot = self.robots[position]
        for key, value in kwargs.items():
            if hasattr(robot, key):
                setattr(robot, key, value)
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'GraspConfig':
        """从YAML配置文件加载配置"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 创建默认配置实例
        config = cls()
        
        # 更新相机配置
        if 'cameras' in config_data:
            for position, camera_data in config_data['cameras'].items():
                if position in config.cameras:
                    config.update_camera_params(position, **camera_data)
        
        # 更新机械臂配置
        if 'robots' in config_data:
            for position, robot_data in config_data['robots'].items():
                if position in config.robots:
                    config.update_robot_params(position, **robot_data)
        
        # 更新其他配置
        if 'rgb_camera_id' in config_data:
            config.rgb_camera_id = config_data['rgb_camera_id']
        if 'sam_model_path' in config_data:
            config.sam_model_path = config_data['sam_model_path']
        
        return config
    
    def to_yaml(self, config_path: str):
        """保存配置到YAML文件"""
        config_data = {
            'cameras': {
                position: asdict(camera) for position, camera in self.cameras.items()
            },
            'robots': {
                position: asdict(robot) for position, robot in self.robots.items()
            },
            'rgb_camera_id': self.rgb_camera_id,
            'sam_model_path': self.sam_model_path
        }
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, indent=2)
    
    def load_config(self, config_path: str):
        """加载配置文件并更新当前实例"""
        new_config = self.from_yaml(config_path)
        self.cameras = new_config.cameras
        self.robots = new_config.robots
        self.rgb_camera_id = new_config.rgb_camera_id
        self.sam_model_path = new_config.sam_model_path


# 全局配置实例
# 默认尝试加载配置文件，如果不存在则使用默认配置
_config_path = os.path.join(os.path.dirname(__file__), 'grasp_config.yaml')
if os.path.exists(_config_path):
    grasp_config = GraspConfig.from_yaml(_config_path)
else:
    grasp_config = GraspConfig()
    # 创建默认配置文件
    grasp_config.to_yaml(_config_path)
   
