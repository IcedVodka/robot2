import cv2
import numpy as np
from typing import List, Optional, Tuple
from utils.llm_quest import VisionAPI, ImageInput

class PrescriptionHandler:
    """处方处理器"""
    def __init__(self, camera_id: int, logger):
        self.camera_id = camera_id
        self.logger = logger
        self.cap = None
        self.vision_api = VisionAPI()
        self.medicines = []  # 识别到的药品列表
        self.current_medicine_index = -1
    
    def setup(self) -> bool:
        """初始化相机"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                self.logger.error(f"无法打开相机 {self.camera_id}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"相机初始化失败: {str(e)}")
            return False
    
    def display_and_capture(self) -> Tuple[bool, Optional[np.ndarray]]:
        """显示视频流并在用户确认时捕获图像"""
        if not self.cap or not self.cap.isOpened():
            self.logger.error("相机未初始化")
            return False, None
            
        while True:
            ret, frame = self.cap.read()
            if not ret:
                self.logger.error("无法读取相机图像")
                return False, None
                
            # 显示图像
            cv2.putText(frame, "请将处方放在框内，按回车确认", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
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
        """清理资源"""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
