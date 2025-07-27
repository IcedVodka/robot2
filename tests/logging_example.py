#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logging模块使用示例
演示如何在机器人系统中使用logging进行日志记录
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger, get_logger
import logging


class SensorExample:
    """传感器示例类，演示logging的使用"""
    
    def __init__(self, name: str):
        self.name = name
        # 创建该传感器的logger
        self.logger = logging.getLogger(f"Sensor.{name}")
        
    def connect(self):
        """连接传感器"""
        try:
            # 模拟连接过程
            self.logger.info(f"{self.name} 开始连接...")
            
            # 模拟连接成功
            self.logger.info(f"{self.name} 连接成功")
            return True
            
        except Exception as e:
            self.logger.error(f"{self.name} 连接失败: {e}")
            return False
    
    def read_data(self):
        """读取传感器数据"""
        try:
            # 模拟数据读取
            data = [1, 2, 3, 4, 5]
            self.logger.debug(f"{self.name} 读取数据: {data}")
            return data
            
        except Exception as e:
            self.logger.error(f"{self.name} 数据读取失败: {e}")
            return None
    
    def disconnect(self):
        """断开传感器连接"""
        self.logger.info(f"{self.name} 断开连接")


class RobotController:
    """机器人控制器示例"""
    
    def __init__(self):
        self.logger = logging.getLogger("Robot.Controller")
        
    def move_to_position(self, x, y, z):
        """移动到指定位置"""
        self.logger.info(f"机械臂移动到位置: ({x}, {y}, {z})")
        
        # 模拟移动过程
        if z > 100:
            self.logger.warning("高度过高，可能存在碰撞风险")
        
        # 模拟移动成功
        self.logger.info("移动完成")
    
    def gripper_control(self, action):
        """夹爪控制"""
        if action == "grip":
            self.logger.info("夹爪闭合")
        elif action == "release":
            self.logger.info("夹爪张开")
        else:
            self.logger.error(f"未知的夹爪动作: {action}")


def main():
    """主函数，演示logging的使用"""
    
    # 1. 设置日志系统
    print("设置日志系统...")
    setup_logger(log_level=logging.DEBUG)  # 设置为DEBUG级别以显示所有日志
    
    # 2. 创建不同模块的logger
    main_logger = get_logger("Main")
    sensor_logger = get_logger("Sensor.RGB_Camera")
    robot_logger = get_logger("Robot.Controller")
    
    # 3. 记录不同级别的日志
    main_logger.info("机器人系统启动")
    
    # 4. 创建传感器实例
    rgb_sensor = SensorExample("RGB_Camera")
    depth_sensor = SensorExample("Depth_Camera")
    
    # 5. 演示传感器操作
    main_logger.info("开始传感器测试")
    
    # RGB传感器连接
    if rgb_sensor.connect():
        data = rgb_sensor.read_data()
        if data:
            main_logger.info("RGB传感器数据读取成功")
        rgb_sensor.disconnect()
    
    # 深度传感器连接
    if depth_sensor.connect():
        data = depth_sensor.read_data()
        if data:
            main_logger.info("深度传感器数据读取成功")
        depth_sensor.disconnect()
    
    # 6. 机器人控制演示
    robot = RobotController()
    
    # 移动到安全位置
    robot.move_to_position(100, 200, 50)
    
    # 夹爪控制
    robot.gripper_control("grip")
    robot.gripper_control("release")
    
    # 7. 错误处理演示
    try:
        # 模拟一个错误
        raise ValueError("模拟的传感器错误")
    except Exception as e:
        sensor_logger.error(f"传感器错误: {e}")
    
    # 8. 系统关闭
    main_logger.info("机器人系统关闭")
    main_logger.info("=" * 50)


if __name__ == "__main__":
    main() 