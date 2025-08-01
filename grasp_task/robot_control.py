#!/usr/bin/env python3

import time
from Robot.robot.realman_controller import RealmanController
from Robot.sensor.suction_sensor import SuctionController
from utils.vertical_grab.interface import vertical_catch
from utils.others import print_grasp_poses

class RobotController:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.robot = None
        self.suction = None
        self.grasp_pose = None

    def setup(self):
        """初始化机械臂和吸盘"""
        self.robot = RealmanController("grasp_robot")
        self.robot.set_up(self.config.robot_ip, self.config.robot_port)
        self.robot.set_arm_init_joint()

        self.suction = SuctionController()
        self.logger.info("机械臂和吸盘初始化完成")

    def calculate_grasp_pose(self, mask, depth_image, color_intr):
        """计算抓取姿态"""
        state = self.robot.get_state()
        pose = state["pose"]
        self.logger.info(f"当前机械臂姿态: {pose}")

        computed_object_pose, prepared_angle_pose, finally_pose = vertical_catch(
            mask=mask,
            depth_frame=depth_image,
            color_intr=color_intr,
            current_pose=pose,
            adjustment=self.config.adjustment,
            vertical_rx_ry_rz=None,
            rotation_matrix=self.config.rotation_matrix,
            translation_vector=self.config.translation_vector,
            use_point_depth_or_mean=True
        )

        self.grasp_pose = (computed_object_pose, prepared_angle_pose, finally_pose)
        print_grasp_poses(self.grasp_pose[0], self.grasp_pose[1], self.grasp_pose[2], self.logger)
        return True

    def execute_grasp(self) -> bool:
        """执行抓取动作"""
        if not self.grasp_pose:
            self.logger.error("未计算抓取姿态")
            return False

        try:
            self.suction.suck()
            self.robot.set_pose_block(self.grasp_pose[1], linear=False)
            time.sleep(2)
            self.robot.set_pose_block(self.grasp_pose[2], linear=True)
            time.sleep(2)
            return True
        except Exception as e:
            self.logger.error(f"执行抓取失败: {str(e)}")
            return False

    def reset_position(self) -> bool:
        """复位机械臂"""
        try:
            self.robot.set_pose_block(self.grasp_pose[1], linear=True)
            time.sleep(1.5)
            self.robot.set_arm_init_joint()
            time.sleep(1.5)
            self.robot.set_arm_fang_joint()
            self.suction.release()
            time.sleep(1.5)
            self.robot.set_arm_init_joint()
            time.sleep(1)
            return True
        except Exception as e:
            self.logger.error(f"复位失败: {str(e)}")
            return False

    def cleanup(self):
        """清理资源"""
        if self.suction:
            self.suction.close()
