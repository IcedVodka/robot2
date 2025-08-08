#!/usr/bin/env python3
from typing import Optional, Dict, Literal, List
import numpy as np
import yaml
import os
from dataclasses import dataclass, asdict
from Robot.robot.realman_controller import RobotParams

@dataclass
class CameraParams:
    """相机参数类"""
    serial: str
    resolution: List[int]
    rotation_matrix: List[List[float]]
    translation_vector: List[float]
    color_intr: Dict[str, float]  # {ppx, ppy, fx, fy}
    


class GraspConfig:
    def __init__(self):
        # 初始化空配置，必须从配置文件加载
        self.cameras = {}
        self.robots = {}
        self.rgb_camera_id = None
        self.sam_model_path = None
    
    def get_camera_params(self, position: Literal['left', 'center', 'right']) -> CameraParams:
        """获取指定位置的相机参数"""
        if position not in self.cameras:
            raise KeyError(f"相机位置 '{position}' 未在配置中找到")
        return self.cameras[position]
    
    def get_robot_params(self, position: Literal['left', 'right']) -> RobotParams:
        """获取指定位置的机械臂参数"""
        if position not in self.robots:
            raise KeyError(f"机械臂位置 '{position}' 未在配置中找到")
        return self.robots[position]
    
    def update_camera_params(self, position: Literal['left', 'center', 'right'], **kwargs):
        """更新相机参数"""
        if position not in self.cameras:
            raise KeyError(f"相机位置 '{position}' 未在配置中找到")
        camera = self.cameras[position]
        for key, value in kwargs.items():
            if hasattr(camera, key):
                setattr(camera, key, value)
    
    def update_robot_params(self, position: Literal['left', 'right'], **kwargs):
        """更新机械臂参数"""
        if position not in self.robots:
            raise KeyError(f"机械臂位置 '{position}' 未在配置中找到")
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
        
        # 创建配置实例
        config = cls()
        
        # 加载相机配置
        if 'cameras' in config_data:
            for position, camera_data in config_data['cameras'].items():
                config.cameras[position] = CameraParams(
                    serial=camera_data['serial'],
                    resolution=camera_data['resolution'],
                    rotation_matrix=camera_data['rotation_matrix'],
                    translation_vector=camera_data['translation_vector'],
                    color_intr=camera_data['color_intr']  # 现在是 {ppx, ppy, fx, fy} 字典
                )
        else:
            raise ValueError("配置文件中缺少 'cameras' 配置")
        
        # 加载机械臂配置
        if 'robots' in config_data:
            for position, robot_data in config_data['robots'].items():
                config.robots[position] = RobotParams(
                    ip=robot_data['ip'],
                    port=robot_data['port'],
                    adjustment=robot_data['adjustment'],
                    arm_init_joints=robot_data['arm_init_joints'],
                    arm_move_speed=robot_data['arm_move_speed'],
                    arm_fang_joints=robot_data['arm_fang_joints'],
                    grip_angles=robot_data['grip_angles'],
                    release_angles=robot_data['release_angles']
                )
        else:
            raise ValueError("配置文件中缺少 'robots' 配置")
        
        # 加载其他配置
        if 'rgb_camera_id' in config_data:
            config.rgb_camera_id = config_data['rgb_camera_id']
        else:
            raise ValueError("配置文件中缺少 'rgb_camera_id' 配置")
            
        if 'sam_model_path' in config_data:
            config.sam_model_path = config_data['sam_model_path']
        else:
            raise ValueError("配置文件中缺少 'sam_model_path' 配置")
        
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
# 必须从配置文件加载，如果配置文件不存在则抛出异常
_config_path = os.path.join(os.path.dirname(__file__), 'grasp_config.yaml')
if os.path.exists(_config_path):
    grasp_config = GraspConfig.from_yaml(_config_path)
    print("已加载配置:")
    print(f"RGB相机ID: {grasp_config.rgb_camera_id}")
    print(f"SAM模型路径: {grasp_config.sam_model_path}")
    print("相机配置:")
    for pos, camera in grasp_config.cameras.items():
        print(f"  {pos}: 序列号={camera.serial}, 分辨率={camera.resolution}")
    print("机械臂配置:")
    for pos, robot in grasp_config.robots.items():
        print(f"  {pos}: IP={robot.ip}:{robot.port}, 速度={robot.arm_move_speed}%")
else:
    raise FileNotFoundError(f"配置文件不存在: {_config_path}，请确保配置文件存在并包含所有必需的配置项")
   
