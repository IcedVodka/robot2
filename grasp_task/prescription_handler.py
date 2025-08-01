import cv2
import logging
import numpy as np
from typing import List, Optional, Tuple
from utils.llm_quest import VisionAPI, ImageInput
from Robot.sensor.rgb_camera import RgbCameraSensor
from grasp_task.config import GraspConfig

class PrescriptionHandler:
    """处方处理器，用于处方图像的采集和识别"""
    def __init__(self, config: 'GraspConfig', logger: 'logging.Logger'):
        """初始化处方处理器
        
        Args:
            config (GraspConfig): 配置对象，包含相机参数等配置信息
            logger (logging.Logger): 日志记录器对象
        """
        self.config = config
        self.logger = logger
        self.sensor = None
        self.vision_api = VisionAPI()
        self.medicines = []  # 识别到的药品列表
        self.current_medicine_index = -1
    
    def setup(self) -> bool:
        """初始化相机"""
        try:
            self.sensor = RgbCameraSensor("prescription_camera")
            self.sensor.set_up(camera_id=self.config.rgb_camera_id)  # 使用默认相机ID 0
            self.logger.info("处方相机初始化完成")
            return True
        except Exception as e:
            self.logger.error(f"相机初始化失败: {str(e)}")
            return False
    
    def display_and_capture(self) -> Tuple[bool, Optional[np.ndarray]]:
        """显示视频流并在用户确认时捕获图像
        
        Returns:
            Tuple[bool, Optional[np.ndarray]]: 
                - bool: 是否成功捕获图像
                - Optional[np.ndarray]: 捕获的图像数据，失败时为None
        """
        if not self.sensor:
            self.logger.error("相机未初始化")
            return False, None
            
        while True:
            data = self.sensor.get_information()
            if not data or "color" not in data:
                self.logger.error("无法读取相机图像")
                return False, None
                
            frame = data["color"]                

            cv2.imshow("Prescription Camera", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                cv2.destroyAllWindows()
                return False, None
            elif key == 13:  # Enter
                cv2.destroyAllWindows()
                return True, frame
    
    def recognize_prescription(self, image: np.ndarray) -> bool:
        """识别处方中的药品列表"""
        try:
            # 创建图像输入对象
            image_input = ImageInput(image_np=image)
            
            # 调用API识别药品
            self.medicines = self.vision_api.extract_prescription_medicines(image_input)
            
            if not self.medicines:
                self.logger.error("未识别到任何药品")
                return False
                
            self.logger.info(f"识别到的药品: {self.medicines}")
            self.current_medicine_index = -1
            return True
            
        except Exception as e:
            self.logger.error(f"处方识别失败: {str(e)}")
            return False
    
    def next_medicine(self) -> Optional[str]:
        """获取下一个需要抓取的药品"""
        if not self.medicines:
            return None
            
        self.current_medicine_index += 1
        if self.current_medicine_index >= len(self.medicines):
            return None
            
        medicine = self.medicines[self.current_medicine_index]
        self.logger.info(f"当前处理药品 [{self.current_medicine_index + 1}/{len(self.medicines)}]: {medicine}")
        return medicine
    
    def cleanup(self):
        """清理相机等资源"""
        if self.sensor:
            self.sensor.cleanup()
        cv2.destroyAllWindows()
