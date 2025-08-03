import cv2
import numpy as np
import time
from dex_retargeting.retargeting_config import RetargetingConfig
from dex_retargeting.seq_retarget import SeqRetargeting
from utils.single_hand_detector import SingleHandDetector
from utils.debug_print import debug_print
from Robot.RealmanController import *

# 设置numpy打印格式，统一显示为小数点后4位
np.set_printoptions(precision=4, suppress=True)


class HandController:
    """
    灵巧手控制器类
    用于手势检测、重定向计算和可视化
    """
    
    def __init__(self, robot_dir, config_path, hand_type="Right", selfie=False):
        """
        初始化控制器
        
        Args:
            robot_dir (str): 机器人模型目录路径
            config_path (str): 重定向配置文件路径
            hand_type (str): 手部类型 ("Right" 或 "Left")
            selfie (bool): 是否为自拍模式
        """
        self.robot_dir = robot_dir
        self.config_path = config_path
        self.hand_type = hand_type
        self.selfie = selfie
        
        # 初始化重定向配置
        RetargetingConfig.set_default_urdf_dir(str(robot_dir))
        self.retargeting = RetargetingConfig.load_from_file(config_path).build()
        
        # 初始化手势检测器
        self.detector = SingleHandDetector(hand_type=hand_type, selfie=selfie)
        
        # 初始化摄像头
        self.cap = None
        self.init_camera()
        
        # FPS计算相关变量
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.fps = 0
        
        # 目标关节索引
        self.target_indices = [8, 0, 2, 6, 4, 10]
         
        # 标定相关变量
        self.calibration_min = np.full(6, np.inf)  # 每个关节的最小值
        self.calibration_max = np.full(6, -np.inf)  # 每个关节的最大值
        self.is_calibrated = False
        
        debug_print("retargeting.joint_names", self.retargeting.joint_names)

        self.master = None
        self.slave = None
        self.teleop = None
        self.init_robot()
    
    def init_camera(self):
        """初始化摄像头"""
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("无法打开摄像头")
    
    def init_robot(self):
        """初始化机械臂"""
        self.master = RealmanController("Master")
        self.slave = RealmanController("Slave")
        self.master.set_up("192.168.1.19", 8080)  # 修改为你的 master 机械臂 IP
        self.slave.set_up("192.168.1.18", 8080)   # 修改为你的 slave 机械臂 IP
        self.master.set_arm_init_joint()
        self.slave.set_arm_init_joint()
        time.sleep(3)
        self.teleop = TeleoperationController(self.master, self.slave, fps=100)
        self.teleop.start()
    
    def calculate_fps(self):
        """计算并更新FPS"""
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.fps_start_time >= 1.0:
            self.fps = self.fps_counter / (current_time - self.fps_start_time)
            self.fps_counter = 0
            self.fps_start_time = current_time
    
    def detect_hand_gesture(self, frame):
        """
        检测手势并计算重定向
        
        Args:
            frame: 输入图像帧
            
        Returns:
            tuple: (targetpos, frame_with_skeleton, has_detection)
        """
        # 转换为RGB格式用于MediaPipe处理
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 检测手势
        num_box, joint_pos, keypoint_2d, mediapipe_wrist_rot = self.detector.detect(rgb_image)
        
        if num_box > 0:
            # 在图像上绘制关键点
            frame_with_skeleton = self.detector.draw_skeleton_on_image(frame, keypoint_2d, style="white")
            
            # 计算重定向
            targetpos = self._calculate_retargeting(joint_pos)
            
            return targetpos, frame_with_skeleton, True
        else:
            return None, frame, False
    
    def _calculate_retargeting(self, joint_pos):
        """
        计算重定向结果
        
        Args:
            joint_pos: 关节位置数据
            
        Returns:
            np.ndarray: 目标位置数组
        """
        retargeting_type = self.retargeting.optimizer.retargeting_type
        indices = self.retargeting.optimizer.target_link_human_indices
        
        if retargeting_type == "POSITION":
            indices = indices
            ref_value = joint_pos[indices, :]
        else:
            origin_indices = indices[0, :]
            task_indices = indices[1, :]
            ref_value = (
                joint_pos[task_indices, :] - joint_pos[origin_indices, :]
            )
        
        qpos = self.retargeting.retarget(ref_value)
        
        # 提取指定索引的targetpos
        targetpos = qpos[self.target_indices]
        debug_print("targetpos", targetpos)
        
        return targetpos
    
    def update_calibration(self, targetpos):
        """
        更新标定数据
        
        Args:
            targetpos: 目标位置数组
        """
        if targetpos is not None:
            self.calibration_min = np.minimum(self.calibration_min, targetpos)
            self.calibration_max = np.maximum(self.calibration_max, targetpos)
    
    def linear_map_to_65535(self, targetpos):
        """
        将targetpos线性映射到0-65535范围
        
        Args:
            targetpos: 目标位置数组
            
        Returns:
            np.ndarray: 映射后的位置数组 (0-65535)
        """
        if not self.is_calibrated:
            return None
        
        # 避免除零错误
        range_values = self.calibration_max - self.calibration_min
        range_values = np.where(range_values == 0, 1, range_values)  # 如果范围为0，设为1
        
        # 线性映射到0-65535
        mapped_pos = ((targetpos - self.calibration_min) / range_values) * 65535
        mapped_pos = np.clip(mapped_pos, 0, 65535)  # 确保在范围内
        
        return mapped_pos.astype(np.uint16)
    
    def draw_calibration_info(self, frame, phase):
        """在图像上绘制标定信息"""
        if phase == "calibration":
            cv2.putText(frame, "CALIBRATION PHASE", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, "Press 'q' to finish calibration", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            # 显示当前标定范围
            if np.any(self.calibration_min != np.inf):
                cv2.putText(frame, f"Min: {self.calibration_min}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                cv2.putText(frame, f"Max: {self.calibration_max}", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        else:
            cv2.putText(frame, "OPERATION PHASE", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, "Press 'q' to exit", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    
    def draw_fps(self, frame):
        """在图像上绘制FPS信息"""
        fps_text = f"FPS: {self.fps:.1f}"
        cv2.putText(frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return frame
    
    def get_target_positions(self, phase="calibration"):
        """
        获取当前的目标位置
        
        Args:
            phase: 当前阶段 ("calibration" 或 "operation")
            
        Returns:
            tuple: (targetpos, mapped_pos, frame_with_skeleton, has_detection)
        """
        ret, frame = self.cap.read()
        if not ret:
            return None, None, frame, False
        
        # 计算FPS
        self.calculate_fps()
        
        # 检测手势
        targetpos, frame_with_skeleton, has_detection = self.detect_hand_gesture(frame)
        
        # 绘制FPS和阶段信息
        frame_with_skeleton = self.draw_fps(frame_with_skeleton)
        self.draw_calibration_info(frame_with_skeleton, phase)
        
        # 显示图像
        cv2.imshow('Hand Gesture Recognition', frame_with_skeleton)
        
        if has_detection and targetpos is not None:
            if phase == "calibration":
                # 标定阶段：更新标定数据
                self.update_calibration(targetpos)
                return targetpos, None, frame_with_skeleton, True
            else:
                # 操作阶段：进行线性映射
                mapped_pos = self.linear_map_to_65535(targetpos)
                return targetpos, mapped_pos, frame_with_skeleton, True
        else:
            return None, None, frame_with_skeleton, False
    
    def run(self):


        """运行主循环"""
        print("=== 标定阶段 ===")
        print("请移动手部进行标定，按 'q' 键完成标定")
        
        # 第一阶段：标定
        while True:
            targetpos, _, frame, has_detection = self.get_target_positions("calibration")
            
            # 检查按键
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # 完成标定
        self.is_calibrated = True
        print("标定完成！")
        print(f"最小值: {self.calibration_min}")
        print(f"最大值: {self.calibration_max}")
        
        print("\n=== 操作阶段 ===")
        print("现在开始操作灵巧手，按 'q' 键退出")
        
        # 第二阶段：操作
        while True:
            targetpos, mapped_pos, frame, has_detection = self.get_target_positions("operation")
            
            if has_detection and mapped_pos is not None:
                # 这里可以添加控制灵巧手的代码
                self.control_robot_hand(mapped_pos)

                print(f"映射后的位置: {mapped_pos}")
                pass
            
            # 检查按键
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    def control_robot_hand(self, mapped_pos):
        """
        控制机器人手部（待实现）
        
        Args:
            mapped_pos: 映射后的位置数组 (0-65535)
        """
        # TODO: 实现机器人手部控制逻辑
        self.slave.set_hand_pos(list(mapped_pos),False)
    
    def release(self):
        """释放资源"""
        if self.teleop is not None:
            self.teleop.stop()
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()


if __name__ == "__main__":
    # 配置参数
    robot_dir = "/home/gml-cwl/code/my_robot/assets/robots/hands"
    config_path = "/home/gml-cwl/code/my_robot/assets/hand_teleop_config/inspire_hand_right_dexpilot.yml"
    
    # 使用上下文管理器确保资源正确释放
    with HandController(robot_dir, config_path, hand_type="Right", selfie=False) as controller:
        controller.run()



