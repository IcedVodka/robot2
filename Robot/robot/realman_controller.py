import yaml
from utils.logger import get_logger
from Robotic_Arm.rm_robot_interface import *
import time
import numpy as np
import threading
import queue
from typing import List, Tuple, Dict, Any, Optional

# Realman机械臂控制器类
class RealmanController:
    """
    Realman机械臂控制器类
    
    提供对单个机械臂的完整控制功能，包括关节控制、灵巧手控制、
    状态监控和错误处理。
    
    Attributes:
        name (str): 控制器名称，用于日志标识
        robot (RoboticArm): 机械臂接口对象
        handle (rm_robot_handle): 机械臂句柄
        is_hand (bool): 末端是否为手
    """
    
    def __init__(self, name: str, is_hand: bool = False):
        """
        初始化机械臂控制器
        
        Args:
            name (str): 控制器名称，用于日志输出标识
            is_hand (bool): 末端是否为手
        """
        self.name = name
        self.is_hand = is_hand
        self.logger = get_logger(name)
        self.robot: Optional[RoboticArm] = None
        self.handle: Optional[rm_robot_handle] = None
        # 读取配置
        try:
            with open('configs/robot_config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 正确访问嵌套的配置结构
            robot_config = config.get('robot', {})
            hand_config = robot_config.get('hand', {})
            
            self.hand_grip_angles = hand_config.get('grip_angles', [1000, 14000, 14000, 14000, 14000, 10000])
            self.hand_release_angles = hand_config.get('release_angles', [4000, 17800, 17800, 17800, 17800, 10000])
            self.arm_init_joints = robot_config.get('arm_init_joints', [0, 0, 90, 0, 90, 0])
            self.arm_fang_joints = robot_config.get('arm_fang_joints',  [-90, 0, 90, 0, 90, 0])
            self.arm_move_speed = robot_config.get('arm_move_speed', 20)
            self.logger.info(f"读取robot_config.yaml成功，hand_grip_angles: {self.hand_grip_angles}, hand_release_angles: {self.hand_release_angles}, arm_init_joints: {self.arm_init_joints}, arm_fang_joints: {self.arm_fang_joints}, arm_move_speed: {self.arm_move_speed}")
        except Exception as e:
            self.logger.warning(f"读取robot_config.yaml失败，使用默认参数: {e}")
            self.hand_grip_angles = [1000, 14000, 14000, 14000, 14000, 10000]
            self.hand_release_angles = [4000, 17800, 17800, 17800, 17800, 10000]
            self.arm_init_joints = [0, 0, 90, 0, 90, 0]
            self.arm_fang_joints =  [-90, 0, 90, 0, 90, 0]

    def set_up(self, rm_ip: str, port: int) -> None:
        """
        设置并连接机械臂
        """
        try:
            self.robot = RoboticArm(rm_thread_mode_e.RM_TRIPLE_MODE_E)
            self.handle = self.robot.rm_create_robot_arm(rm_ip, port)
            self.logger.info(f"机械臂ID：{self.handle.id}")
            ret, joint_angles = self.robot.rm_get_joint_degree()
            if ret == 0:
                self.logger.info(f"当前机械臂各关节角度：{joint_angles}")
            else:
                self.logger.error(f"读取关节角度失败，错误码：{ret}")
        except Exception as e:
            self.logger.error(f"Failed to initialize robot arm: {str(e)}")
            raise ConnectionError(f"Failed to initialize robot arm: {str(e)}")

    def reset_zero_position(self, start_angles: Optional[List[float]] = None) -> bool:
        """
        将机械臂移动到零位或指定初始位置
        """
        self.logger.info(f"Moving {self.name} arm to start position...")
        succ, state = self.robot.rm_get_current_arm_state()
        if succ != 0:
            self.logger.error(f"{self.name} arm is not connected or responding")
            return False

        if start_angles is None:
            succ, start_angles = self.robot.rm_get_init_pose()
            if succ != 0:
                self.logger.error(f"Failed to get initial pose for {self.name} arm")
                return False

        try:
            result = self.robot.rm_movej(start_angles, self.arm_move_speed, 0, 0, 1)
            if result == 0:
                self.logger.info(f"{self.name} arm moved to start position")
                succ, state = self.robot.rm_get_current_arm_state()
                if succ == 0:
                    current_joints = state['joint']
                    max_diff = max(abs(np.array(current_joints) - np.array(start_angles)))
                    if max_diff > 0.01:
                        self.logger.warning(f"{self.name} arm position differs from target by {max_diff} radians")
                time.sleep(2)
                return True
            else:
                self.logger.error(f"Failed to move {self.name} arm. Error code: {result}")
                return False
        except Exception as e:
            self.logger.error(f"Exception while moving {self.name} arm: {str(e)}")
            return False

    def get_state(self) -> Dict[str, Any]:
        """
        获取机械臂当前状态
        """
        succ, arm_state = self.robot.rm_get_current_arm_state()
        if succ != 0 or arm_state is None:
            self.logger.error("Failed to get arm state")
            raise RuntimeError("Failed to get arm state")
        state = arm_state.copy()
        return state

    def set_arm_joints(self, joint: List[float]) -> None:
        """
        设置机械臂关节角度，直接透传给机械臂，不进行阻塞实时返回
        """
        try:
            if len(joint) != 6:
                self.logger.error(f"Invalid joint length: {len(joint)}, expected 6")
                raise ValueError(f"Invalid joint length: {len(joint)}, expected 6")
            success = self.robot.rm_movej_canfd(joint, False, 0, 0, 0)
            if success != 0:
                self.logger.error("Failed to set joint angles")
                raise RuntimeError("Failed to set joint angles")
        except Exception as e:
            self.logger.error(f"Error moving robot: {str(e)}")
            raise RuntimeError(f"Error moving robot: {str(e)}")
        
    def set_arm_joints_block(self, joint: List[float]) -> None:
        """
        设置机械臂关节角度，阻塞模式，等待机械臂到达目标位置或规划失败后才返回
        """
        try:
            if len(joint) != 6:
                self.logger.error(f"Invalid joint length: {len(joint)}, expected 6")
                raise ValueError(f"Invalid joint length: {len(joint)}, expected 6")
            success = self.robot.rm_movej(joint, self.arm_move_speed, 0, 0, 1)
            if success != 0:
                self.logger.error("Failed to set joint angles")
                raise RuntimeError("Failed to set joint angles")
        except Exception as e:
            self.logger.error(f"Error moving robot: {str(e)}")
            raise RuntimeError(f"Error moving robot: {str(e)}")

    def set_arm_init_joint(self) -> None:
        """
        将机械臂移动到全局变量arm_init_joints定义的初始位置
        """
        self.set_arm_joints_block(self.arm_init_joints)

    def set_arm_fang_joint(self) -> None:
        """
        将机械臂移动到放置位置（arm_fang_joints定义的位置）
        """
        self.set_arm_joints_block(self.arm_fang_joints)

    def set_pose_block(self, pose: List[float],linear: bool = True) -> None:
        """
        将机械臂末端移动到指定位置
        """
        try:
            if len(pose) != 6:
                self.logger.error(f"Invalid joint length: {len(pose)}, expected 6")
                raise ValueError(f"Invalid joint length: {len(pose)}, expected 6")
            if linear:
                success = self.robot.rm_movel(pose, self.arm_move_speed, 0, 0, 1)
            else:
                success = self.robot.rm_movej_p(pose, self.arm_move_speed, 0, 0, 1)
            if success != 0:
                self.logger.error("Failed to set joint angles")
                raise RuntimeError("Failed to set joint angles")
        except Exception as e:
            self.logger.error(f"Error moving robot: {str(e)}")
            raise RuntimeError(f"Error moving robot: {str(e)}")

    def set_hand_angle(self, hand_angle: List[int], block: bool = True, timeout: int = 10) -> int:
        if not self.is_hand:
            self.logger.error("当前控制器不是灵巧手，无法设置手角度")
            raise RuntimeError("当前控制器不是灵巧手，无法设置手角度")
        try:
            if not isinstance(hand_angle, (list, tuple)) or len(hand_angle) != 6:
                self.logger.error(f"Invalid hand_angle, must be list of 6 ints, got: {hand_angle}")
                raise ValueError(f"Invalid hand_angle, must be list of 6 ints, got: {hand_angle}")
            tag = self.robot.rm_set_hand_follow_angle(hand_angle, block)
            if tag != 0:
                self.logger.error(f"Failed to set hand angle, error code: {tag}")
                raise RuntimeError(f"Failed to set hand angle, error code: {tag}")
            return tag
        except Exception as e:
            self.logger.error(f"Error setting hand angle: {str(e)}")
            raise RuntimeError(f"Error setting hand angle: {str(e)}")

    def set_hand_pos(self, hand_pos: List[int], block: bool = True, timeout: int = 10) -> int:
        if not self.is_hand:
            self.logger.error("当前控制器不是灵巧手，无法设置手位置")
            raise RuntimeError("当前控制器不是灵巧手，无法设置手位置")
        try:
            if not isinstance(hand_pos, (list, tuple)) or len(hand_pos) != 6:
                self.logger.error(f"Invalid hand_pos, must be list of 6 ints, got: {hand_pos}")
                raise ValueError(f"Invalid hand_pos, must be list of 6 ints, got: {hand_pos}")
            tag = self.robot.rm_set_hand_follow_pos(hand_pos, block)
            if tag != 0:
                self.logger.error(f"Failed to set hand position, error code: {tag}")
                raise RuntimeError(f"Failed to set hand position, error code: {tag}")
            return tag
        except Exception as e:
            self.logger.error(f"Error setting hand position: {str(e)}")
            raise RuntimeError(f"Error setting hand position: {str(e)}")

    def grip_hand(self, block: bool = True) -> int:
        if not self.is_hand:
            self.logger.error("当前控制器不是灵巧手，无法执行夹紧操作")
            raise RuntimeError("当前控制器不是灵巧手，无法执行夹紧操作")
        return self.set_hand_angle(self.hand_grip_angles, block=block)

    def release_hand(self, block: bool = True) -> int:
        if not self.is_hand:
            self.logger.error("当前控制器不是灵巧手，无法执行松开操作")
            raise RuntimeError("当前控制器不是灵巧手，无法执行松开操作")
        return self.set_hand_angle(self.hand_release_angles, block=block)

    def __del__(self):
        """
        析构函数，确保在对象销毁时断开机械臂连接
        """
        try:
            if self.robot is not None:
                handle = self.robot.rm_delete_robot_arm()
                if handle == 0:
                    self.logger.info("\nSuccessfully disconnected from the robot arm\n")
                else:
                    self.logger.warning("\nFailed to disconnect from the robot arm\n")
        except Exception as e:
            self.logger.error(f"Error during disconnect in __del__: {e}") 


