#!/usr/bin/env python3

import sys
import os
import logging
from utils.logger import setup_logger, get_logger
from policy.segmentation import SamPredictor
import cv2

# 添加项目路径
sys.path.append(os.path.abspath('.'))

from .config import GraspConfig
from .image_handler import ImageHandler
from .point_selector import PointSelector
from .robot_control import RobotController
from .prescription_handler import PrescriptionHandler

class GraspTask:
    def __init__(self):
        self.logger = get_logger("GraspTask")
        self.config = GraspConfig()
        
        # 初始化各个模块
        self.image_handler = ImageHandler(self.config, self.logger)
        self.point_selector = PointSelector(self.image_handler, self.logger)
        self.robot_controller = RobotController(self.config, self.logger)
        self.prescription_handler = PrescriptionHandler(camera_id=1, logger=self.logger)
        
        # SAM模型
        self.sam_model = None
        self.mask_result = None #记得及时清空
        self.prescription_frame = None
        self.grasp_machine = None
        
        self._init_components()
        
    def _init_components(self):
        """初始化所有组件"""
        try:
            self.sam_model = SamPredictor(self.config.sam_model_path)
            self.image_handler.setup()
            self.robot_controller.setup()
            self.prescription_handler.setup()
            self.logger.info("所有组件初始化完成")
            return True
        except Exception as e:
            self.logger.error(f"组件初始化失败: {str(e)}")
            return False
            
    def run_prescription_display(self) -> bool:
        """运行处方展示和捕获阶段"""
        self.logger.info("=== 处方展示阶段 ===")
        self.logger.info("请将处方放在摄像头下方")
        
        success, frame = self.prescription_handler.display_and_capture()
        if not success:
            self.prescription_frame = None
            self.logger.error("处方图像捕获失败")
            return False
            
        self.logger.info("处方图像捕获成功")
        self.prescription_frame = frame
        return True
        
    def run_prescription_recognition(self) -> bool:
        """运行处方识别阶段"""
        self.logger.info("=== 处方识别阶段 ===")
        success = self.prescription_handler.recognize_prescription(self.prescription_frame)
        self.prescription_frame = None  # 清理处方图像
        if not success:
            self.logger.error("处方识别失败")
            return False
        return True
        
    def run_medicine_selection(self) -> bool:
        """选择下一个要抓取的药品"""
        medicine = self.prescription_handler.next_medicine()
        self.garaph_machine = medicine
        if medicine is None:
            self.logger.info("所有药品处理完成")            
            return False
        
        self.logger.info(f"准备抓取药品: {medicine}")
        return True

    def run_point_selection(self) -> bool:
        """运行点选择阶段"""
        self.logger.info("=== 阶段1: 图像展示和点选择 ===")
        
        print("\n请选择点选择模式:")
        print("1. 手动选择 (点击选择目标点)")
        print("2. 大模型自动选择")
        
        while True:
            try:
                choice = input("请输入选择 (1 或 2): ").strip()
                if choice in ['1', '2']:
                    break
                print("无效选择，请输入 1 或 2")
            except KeyboardInterrupt:
                return False
        
        return self.point_selector.manual_select() if choice == '1' else self.point_selector.ai_select(self.grasp_machine)

    def run_segmentation(self) -> bool:
        """运行分割阶段"""
        self.logger.info("=== 阶段2: SAM分割推理 ===")
        
        if self.image_handler.last_color_image is None:
            self.logger.error("缺少图像数据")
            return False
        
        try:
            rgb_image = cv2.cvtColor(self.image_handler.last_color_image, cv2.COLOR_BGR2RGB)
            center, mask = self.sam_model.predict(rgb_image, points=self.point_selector.selected_point)
            
            if mask is not None:
                self.mask_result = mask
                self.logger.info(f"SAM分割成功，中心点: {center}")
                cv2.imshow("SAM Segmentation Result", mask)
                
                # 计算抓取位置
                success = self.robot_controller.calculate_grasp_pose(
                    mask=self.mask_result,
                    depth_image=self.image_handler.last_depth_image,
                    color_intr=self.config.color_intr
                )
                
                if not success:
                    self.logger.error("抓取位置计算失败")
                    return False
                
                self.logger.info("抓取位置计算完成")
                cv2.waitKey(0)
                cv2.destroyAllWindows()
                return True
            else:
                self.logger.warning("SAM分割失败，未得到有效掩码")
                return False
                
        except Exception as e:
            self.logger.error(f"分割阶段失败: {str(e)}")
            return False

    def run_grasp(self) -> bool:
        """运行抓取阶段"""
        self.logger.info("=== 阶段3: 机械臂抓取 ===")
        return self.robot_controller.execute_grasp()

    def run_reset(self) -> bool:
        """运行复位阶段"""
        self.logger.info("=== 阶段4: 机械臂复位 ===")
        return self.robot_controller.reset_position()

    def run(self):
        """主运行循环"""
        from .states import GraspState, StateMachine
        
        self.logger.info("基于处方的机械臂抓取系统启动")
        self.logger.info("程序将按以下阶段运行:")
        self.logger.info("阶段1: 处方展示和确认")
        self.logger.info("阶段2: 处方识别")
        self.logger.info("阶段3: 药品选择")
        self.logger.info("阶段4: 目标点选择")
        self.logger.info("阶段5: 目标分割")
        self.logger.info("阶段6: 机械臂抓取")
        self.logger.info("阶段7: 机械臂复位")
        self.logger.info("按ESC键退出程序，按Ctrl+C中断当前操作")
        
        # 启用调试模式
        debug_mode = True
        if debug_mode:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("调试模式已启用")
        
        # 创建状态机
        state_machine = StateMachine(self.logger)
        
        # 注册状态处理器
        state_machine.register_handler(GraspState.PRESCRIPTION_DISPLAY, self.run_prescription_display)
        state_machine.register_handler(GraspState.PRESCRIPTION_RECOGNITION, self.run_prescription_recognition)
        state_machine.register_handler(GraspState.MEDICINE_SELECTION, self.run_medicine_selection)
        state_machine.register_handler(GraspState.POINT_SELECTION, self.run_point_selection)
        state_machine.register_handler(GraspState.SEGMENTATION, self.run_segmentation)
        state_machine.register_handler(GraspState.GRASPING, self.run_grasp)
        state_machine.register_handler(GraspState.RESETTING, self.run_reset)
        state_machine.register_handler(GraspState.FINISHED, self._handle_finished)
        state_machine.register_handler(GraspState.ERROR, self._handle_error)
        
        try:
            # 开始状态机循环
            while state_machine.current_state not in [GraspState.IDLE, GraspState.ERROR]:
                # 运行当前状态的处理器
                result = state_machine.run()
                
                # 转换到下一个状态
                next_state = state_machine.transition(result)
                if next_state is None:
                    break
                
        except KeyboardInterrupt:
            self.logger.info("用户中断程序")
        except Exception as e:
            self.logger.error(f"程序运行异常: {str(e)}")
        finally:
            self.cleanup()

    def _handle_finished(self) -> bool:
        """处理完成状态"""
        self.logger.info("一个完整周期完成，准备开始下一轮...")
        try:
            input("按回车键开始下一轮...")
            return True  # 继续下一轮
        except KeyboardInterrupt:
            return False  # 退出程序
    
    def _handle_error(self) -> bool:
        """处理错误状态"""
        self.logger.error("程序进入错误状态，即将退出...")
        return False  # 退出程序
    
    def cleanup(self):
        """清理资源"""
        self.logger.info("正在清理资源...")
        self.image_handler.cleanup()
        self.robot_controller.cleanup()
        self.logger.info("资源清理完成")

def main():
    """主函数"""
    setup_logger(log_level=logging.DEBUG, enable_color=True)
    task = GraspTask()
    task.run()

if __name__ == "__main__":
    main()
