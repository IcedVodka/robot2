"""
RealmanController.py

@brief 机械臂控制器模块
@author Realman-Aisha
@date 2024-04-28

@details
此模块提供了对Realman机械臂的高级控制接口，包括：
- 机械臂关节控制
- 灵巧手控制
- 遥操作功能
- 状态监控和错误处理

主要类：
- RealmanController: 单机械臂控制器
- TeleoperationController: 遥操作控制器

@note
- 使用前需要确保机械臂已正确连接
- 所有角度单位为度(°)
- 灵巧手角度范围为0-65535
"""

from Robotic_Arm.rm_robot_interface import *
import time
import numpy as np
import threading
import queue
from typing import List, Tuple, Dict, Any, Optional
from utils.debug_print import debug_print

# 全局常量定义
# 灵巧手夹紧和松开的角度配置
Hand_grip_angles = [1000, 14000, 14000, 14000, 14000, 10000]  # 夹紧状态各关节角度
Hand_release_angles = [4000, 17800, 17800, 17800, 17800, 10000]  # 松开状态各关节角度

# 机械臂初始关节角度配置
Arm_init_joints = [0, 0, 90, 0, 90, 0]  # 6个关节的初始角度


class RealmanController:
    """
    Realman机械臂控制器类
    
    提供对单个机械臂的完整控制功能，包括关节控制、灵巧手控制、
    状态监控和错误处理。
    
    Attributes:
        name (str): 控制器名称，用于日志标识
        robot (RoboticArm): 机械臂接口对象
        handle (rm_robot_handle): 机械臂句柄
    """
    
    def __init__(self, name: str):
        """
        初始化机械臂控制器
        
        Args:
            name (str): 控制器名称，用于日志输出标识
            
        Example:
            >>> controller = RealmanController("left_arm")
        """
        self.name = name
        self.robot: Optional[RoboticArm] = None
        self.handle: Optional[rm_robot_handle] = None

    def set_up(self, rm_ip: str, port: int) -> None:
        """
        设置并连接机械臂
        
        Args:
            rm_ip (str): 机械臂IP地址
            port (int): 通信端口号
            
        Raises:
            ConnectionError: 连接失败时抛出
            
        Example:
            >>> controller.set_up("192.168.1.100", 8080)
        """
        try:
            # 创建机械臂对象，使用三线程模式
            self.robot = RoboticArm(rm_thread_mode_e.RM_TRIPLE_MODE_E)
            
            # 创建机械臂连接
            self.handle = self.robot.rm_create_robot_arm(rm_ip, port)
            debug_print("RealmanController", f"机械臂ID：{self.handle.id}", "INFO")

            # 验证连接并获取当前关节角度
            ret, joint_angles = self.robot.rm_get_joint_degree()
            if ret == 0:
                debug_print("RealmanController", f"当前机械臂各关节角度：{joint_angles}", "INFO")
            else:
                debug_print("RealmanController", f"读取关节角度失败，错误码：{ret}", "ERROR")      
        
        except Exception as e:
            raise ConnectionError(f"Failed to initialize robot arm: {str(e)}")

    def reset_zero_position(self, start_angles: Optional[List[float]] = None) -> bool:
        """
        将机械臂移动到零位或指定初始位置
        
        Args:
            start_angles (Optional[List[float]]): 目标关节角度列表，为None时使用系统默认初始位置
                                                  长度应为6，对应6个关节角度(单位：度)
        
        Returns:
            bool: 移动是否成功
                - True: 移动成功
                - False: 移动失败
                
        Raises:
            RuntimeError: 机械臂未连接或响应异常时抛出
            
        Example:
            >>> success = controller.reset_zero_position()
            >>> success = controller.reset_zero_position([0, 0, 90, 0, 90, 0])
        """
        debug_print(self.name, f"\nMoving {self.name} arm to start position...", "INFO")
        
        # 检查机械臂连接状态
        succ, _ = self.robot.rm_get_current_arm_state()
        if succ != 0:
            debug_print(self.name, f"Error: {self.name} arm is not connected or responding", "ERROR")
            return False
        
        # 获取当前关节位置
        succ, state = self.robot.rm_get_current_arm_state()
        if succ == 0:
            current_joints = state['joint']
            debug_print(self.name, f"Current {self.name} arm position: {current_joints}", "INFO")

        # 获取目标位置
        if start_angles is None:
            succ, start_angles = self.robot.rm_get_init_pose()
            if succ != 0:
                debug_print(self.name, f"Error: {self.name} arm is not connected or responding", "ERROR")
                return False
        
        # 移动到目标位置
        try:
            debug_print(self.name, f"Target {self.name} arm position: {start_angles}", "INFO")
            # 执行关节运动，速度20%，阻塞模式
            result = self.robot.rm_movej(start_angles, 20, 0, 0, 1)
            
            if result == 0:
                debug_print(self.name, f"Successfully moved {self.name} arm to start position", "INFO")
                
                # 验证当前位置
                succ, state = self.robot.rm_get_current_arm_state()
                if succ == 0:
                    current_joints = state['joint']
                    debug_print(self.name, f"New {self.name} arm position: {current_joints}", "INFO")
                    
                    # 检查位置误差
                    max_diff = max(abs(np.array(current_joints) - np.array(start_angles)))
                    if max_diff > 0.01:  # 允许0.01弧度的误差
                        debug_print(self.name, f"Warning: {self.name} arm position differs from target by {max_diff} radians", "WARNING")
                else:
                    debug_print(self.name, f"Warning: Could not verify {self.name} arm position", "WARNING")
                
                # 等待系统稳定
                debug_print(self.name, f"Waiting for {self.name} arm to stabilize...", "INFO")
                time.sleep(2)
                return True
            else:
                debug_print(self.name, f"Failed to move {self.name} arm to start position. Error code: {result}", "ERROR")
                return False
                
        except Exception as e:
            debug_print(self.name, f"Exception while moving {self.name} arm: {str(e)}", "ERROR")
            return False

    def get_state(self) -> Dict[str, Any]:
        """
        获取机械臂当前状态
        
        Returns:
            Dict[str, Any]: 机械臂状态字典，包含关节角度、位置、速度等信息
                - 'joint': List[float] - 当前关节角度(度)
                - 'pose': List[float] - 当前末端位姿
                - 'velocity': List[float] - 当前关节速度
                - 其他状态信息...
                
        Raises:
            RuntimeError: 获取状态失败时抛出
            
        Example:
            >>> state = controller.get_state()
            >>> joint_angles = state['joint']
        """
        # 获取机械臂状态
        succ, arm_state = self.robot.rm_get_current_arm_state()

        if succ != 0 or arm_state is None:
            raise RuntimeError("Failed to get arm state")
        
        state = arm_state.copy()
        return state  
    
    def set_arm_joints(self, joint: List[float]) -> None:
        """
        设置机械臂关节角度
        
        Args:
            joint (List[float]): 目标关节角度列表，长度必须为6
                                对应6个关节的角度值(单位：度)
        
        Raises:
            ValueError: 关节角度列表长度不正确时抛出
            RuntimeError: 设置关节角度失败时抛出
            
        Example:
            >>> controller.set_arm_joints([0, 0, 90, 0, 90, 0])
        """
        try:
            if len(joint) != 6:
                raise ValueError(f"Invalid joint length: {len(joint)}, expected 6")
            
            # 使用CANFD模式设置关节角度，非阻塞模式
            success = self.robot.rm_movej_canfd(joint, False, 0, 0, 0)
            if success != 0:
                raise RuntimeError("Failed to set joint angles")
                
        except Exception as e:
            raise RuntimeError(f"Error moving robot: {str(e)}")
        
    def set_arm_init_joint(self) -> None:
        """
        将机械臂移动到全局变量Arm_init_joints定义的初始位置
        
        Example:
            >>> controller.set_arm_init_joint()
        """
        self.set_arm_joints(Arm_init_joints)

    def set_hand_angle(self, hand_angle: List[int], block: bool = True, timeout: int = 10) -> int:
        """
        设置灵巧手各自由度角度
        
        Args:
            hand_angle (List[int]): 手指角度数组，长度必须为6
                                   范围：0~65535，-1代表该自由度不执行任何操作
            block (bool): 是否阻塞执行
                         - True: 阻塞模式，等待执行完成
                         - False: 非阻塞模式，立即返回
            timeout (int): 阻塞模式下的超时时间(秒)
        
        Returns:
            int: 执行状态码
                - 0: 成功
                - 其他: 失败错误码
                
        Raises:
            ValueError: 参数格式错误时抛出
            RuntimeError: 设置失败时抛出
            
        Example:
            >>> # 夹紧手爪
            >>> controller.set_hand_angle([1000, 14000, 14000, 14000, 14000, 10000])
            >>> # 松开手爪
            >>> controller.set_hand_angle([4000, 17800, 17800, 17800, 17800, 10000])
        """
        try:
            if not isinstance(hand_angle, (list, tuple)) or len(hand_angle) != 6:
                raise ValueError(f"Invalid hand_angle, must be list of 6 ints, got: {hand_angle}")
            
            tag = self.robot.rm_set_hand_follow_angle(hand_angle, block)
            if tag != 0:
                raise RuntimeError(f"Failed to set hand angle, error code: {tag}")
            return tag
            
        except Exception as e:
            raise RuntimeError(f"Error setting hand angle: {str(e)}")
    
    def set_hand_pos(self, hand_pos: List[int], block: bool = True, timeout: int = 10) -> int:
        """
        设置灵巧手位置跟随控制
        
        Args:
            hand_pos (List[int]): 手指位置数组，长度必须为6
                                 最大范围为0-65535，按照灵巧手厂商定义的角度做控制
            block (bool): 是否阻塞执行
                         - True: 阻塞模式，等待执行完成
                         - False: 非阻塞模式，立即返回
            timeout (int): 阻塞模式下的超时时间(秒)
        
        Returns:
            int: 执行状态码
                - 0: 成功
                - 其他: 失败错误码
                
        Raises:
            ValueError: 参数格式错误时抛出
            RuntimeError: 设置失败时抛出
            
        Example:
            >>> controller.set_hand_pos([1000, 14000, 14000, 14000, 14000, 10000])
        """
        try:
            if not isinstance(hand_pos, (list, tuple)) or len(hand_pos) != 6:
                raise ValueError(f"Invalid hand_pos, must be list of 6 ints, got: {hand_pos}")
            
            tag = self.robot.rm_set_hand_follow_pos(hand_pos, block)
            if tag != 0:
                raise RuntimeError(f"Failed to set hand position, error code: {tag}")
            return tag
            
        except Exception as e:
            raise RuntimeError(f"Error setting hand position: {str(e)}")
      
    def __del__(self):
        """
        析构函数，确保在对象销毁时断开机械臂连接
        """
        try:
            if self.robot is not None:
                handle = self.robot.rm_delete_robot_arm()
                if handle == 0:
                    debug_print("RealmanController", "\nSuccessfully disconnected from the robot arm\n", "INFO")
                else:
                    debug_print("RealmanController", "\nFailed to disconnect from the robot arm\n", "WARNING")
        except Exception as e:
            debug_print("RealmanController", f"Error during disconnect in __del__: {e}", "ERROR")


class TeleoperationController:
    """
    遥操作控制器类
    
    实现主从机械臂的遥操作功能，支持实时关节跟随和灵巧手状态控制。
    
    Attributes:
        master (RealmanController): 主机械臂控制器
        slave (RealmanController): 从机械臂控制器
        fps (int): 遥操作频率(Hz)
        hand_state (str): 当前灵巧手状态('open'或'grip')
        prev_hand_state (str): 上一次灵巧手状态
    """
    
    def __init__(self, master: RealmanController, slave: RealmanController, fps: int = 30):
        """
        初始化遥操作控制器
        
        Args:
            master (RealmanController): 主机械臂控制器
            slave (RealmanController): 从机械臂控制器
            fps (int): 遥操作频率，默认30Hz
            
        Example:
            >>> teleop = TeleoperationController(master_arm, slave_arm, fps=30)
        """
        self.master = master
        self.slave = slave
        self.fps = fps
        self._q = queue.Queue(maxsize=10)  # 关节数据队列
        self._running = False
        self._master_thread = None
        self._slave_thread = None



    def _master_collect(self) -> None:
        """
        主机械臂数据采集线程函数
        
        以指定频率采集主机械臂的关节角度数据并放入队列。
        """
        interval = 1.0 / self.fps
        while self._running:
            try:
                state = self.master.get_state()
                joint = state['joint']
                self._q.put(joint, timeout=0.1)
            except Exception as e:
                debug_print("TeleoperationController", f"[Master] Error collecting joint: {e}", "ERROR")
            time.sleep(interval)

    def _slave_play(self) -> None:
        """
        从机械臂执行线程函数
        
        从队列获取关节数据并控制从机械臂执行，同时处理灵巧手状态变化。
        """
        while self._running:
            try:
                joint = self._q.get(timeout=0.5)
                self.slave.set_arm_joints(joint)
            except queue.Empty:
                pass
            except Exception as e:
                debug_print("TeleoperationController", f"[Slave] Error setting joint: {e}", "ERROR")
            

    def start(self) -> None:
        """
        启动遥操作
        
        启动主从机械臂的数据采集和执行线程。
        
        Example:
            >>> teleop.start()
        """
        self._running = True
        self._master_thread = threading.Thread(target=self._master_collect)
        self._slave_thread = threading.Thread(target=self._slave_play)
        self._master_thread.start()
        self._slave_thread.start()
        debug_print("TeleoperationController", "遥操作已启动", "INFO")

    def stop(self) -> None:
        """
        停止遥操作
        
        停止所有遥操作线程并等待线程结束。
        
        Example:
            >>> teleop.stop()
        """
        self._running = False
        if self._master_thread:
            self._master_thread.join()
        if self._slave_thread:
            self._slave_thread.join()
        debug_print("TeleoperationController", "遥操作已停止", "INFO")


   
