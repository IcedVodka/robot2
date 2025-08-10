import yaml
from utils.logger import get_logger
from Robotic_Arm.rm_robot_interface import *
import time
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class RobotParams:
    """机械臂参数类"""
    ip: str
    port: int
    adjustment: List[float] = field(default_factory=lambda: [0.0, 0.0])  # [安全预备位置偏移, 最终抓取位置偏移]
    arm_init_joints: List[float] = field(default_factory=lambda: [0, 0, 90, 0, 90, 0])  # 机械臂6个关节的初始角度
    arm_move_speed: int = 20  # 机械臂运动速度，单位%，范围 1~100
    arm_fang_joints: List[float] = field(default_factory=lambda: [-90, 0, 90, 0, 90, 0])  # 机械臂放物关节角度
    grip_angles: List[int] = field(default_factory=lambda: [1000, 14000, 14000, 14000, 14000, 10000])  # 灵巧手抓取角度配置
    release_angles: List[int] = field(default_factory=lambda: [4000, 17800, 17800, 17800, 17800, 10000])  # 灵巧手释放角度配置

    # def __post_init__(self):
    #     """参数验证"""
    #     if len(self.adjustment) != 2:
    #         raise ValueError("adjustment must have exactly 2 elements")
    #     if len(self.arm_init_joints) != 6:
    #         raise ValueError("arm_init_joints must have exactly 6 elements")
    #     if len(self.arm_fang_joints) != 6:
    #         raise ValueError("arm_fang_joints must have exactly 6 elements")
    #     if len(self.grip_angles) != 6:
    #         raise ValueError("grip_angles must have exactly 6 elements")
    #     if len(self.release_angles) != 6:
    #         raise ValueError("release_angles must have exactly 6 elements")
    #     if not (1 <= self.arm_move_speed <= 100):
    #         raise ValueError("arm_move_speed must be between 1 and 100")

def create_robot_param_from_yaml(config_path: str) -> RobotParams:
    """从YAML文件创建RobotParams实例"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 支持嵌套配置结构
        robot_config = config.get('robot', {})
        return RobotParams(**robot_config)
    except Exception as e:
        raise RuntimeError(f"Failed to load config from {config_path}: {e}")

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
    
    def __init__(self, name: str, params: RobotParams, is_hand: bool = False):
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
        self.modbus_handle = None
        
         # 从参数中获取配置
        self.ip = params.ip
        self.port = params.port
        self.hand_grip_angles = params.grip_angles
        self.hand_release_angles = params.release_angles
        self.arm_init_joints = params.arm_init_joints
        self.arm_fang_joints = params.arm_fang_joints
        self.arm_move_speed = params.arm_move_speed

        self.write_params = rm_peripheral_read_write_params_t(
            port=1,           # 末端接口板RS485接口
            address=0,  # 线圈地址0
            device=1, # 设备地址1
            num=1             # 写入1个线圈
        )
        
        self.read_params = rm_peripheral_read_write_params_t(
            port=1,           # 末端接口板RS485接口
            address=0,  # 线圈地址0
            device=1, # 设备地址1
            num=1             # 读取1个线圈
        )
        
        self.logger.info(f"初始化控制器 {name}，参数: ip={params.ip}, port={params.port}, is_hand={is_hand}")

    def set_up(self) -> None:
        """
        设置并连接机械臂
        """
        try:
            self.robot = RoboticArm(rm_thread_mode_e.RM_TRIPLE_MODE_E)
            self.handle = self.robot.rm_create_robot_arm(self.ip, self.port)
            self.logger.info(f"机械臂ID：{self.handle.id}")
            ret, joint_angles = self.robot.rm_get_joint_degree()
            if ret == 0:
                self.logger.info(f"当前机械臂各关节角度：{joint_angles}")
            else:
                self.logger.error(f"读取关节角度失败，错误码：{ret}")
            self.modbus_handle = self.robot.rm_set_modbus_mode(
                port=1,  # 末端接口板RS485接口
                baudrate=9600,
                timeout=10
            )
            time.sleep(2) 
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
            # if len(joint) != 6:
            #     self.logger.error(f"Invalid joint length: {len(joint)}, expected 6")
            #     raise ValueError(f"Invalid joint length: {len(joint)}, expected 6")
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
            # if len(joint) != 6:
            #     self.logger.error(f"Invalid joint length: {len(joint)}, expected 6")
            #     raise ValueError(f"Invalid joint length: {len(joint)}, expected 6")
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
    
    def suck(self) -> int:
        ret = self.robot.rm_write_single_coil(self.write_params, 1)
        if ret == 0:
            self.logger.info("✓ 线圈0写入1成功, 吸盘吸取")
        else:
            self.logger.error(f"✗ 线圈写入失败，错误码：{ret}, 吸盘吸取失败")
        return ret
    
    def release_suck(self) -> int:
        ret = self.robot.rm_write_single_coil(self.write_params, 0)
        if ret == 0:
            self.logger.info("✓ 线圈0写入0成功, 吸盘释放")
        else:
            self.logger.error(f"✗ 线圈写入失败，错误码：{ret}, 吸盘释放失败")
        return ret

    def __del__(self):
        """
        析构函数，确保在对象销毁时断开机械臂连接
        """
        try:
            if self.modbus_handle is not None:
                ret = self.robot.rm_close_modbus_mode(port=1)
                if ret == 0:
                    self.logger.info("✓ Modbus模式已关闭")
                else:
                    self.logger.error(f"✗ 关闭Modbus模式失败，错误码：{ret}")
            if self.robot is not None:
                handle = self.robot.rm_delete_robot_arm()
                if handle == 0:
                    self.logger.info("\nSuccessfully disconnected from the robot arm\n")
                else:
                    self.logger.warning("\nFailed to disconnect from the robot arm\n")           
        except Exception as e:
            self.logger.error(f"Error during disconnect in __del__: {e}") 


