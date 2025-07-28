import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.models.sam import Predictor as SAMPredictor
from typing import Optional, Tuple, List, Dict, Union
import os

def save_image(image: np.ndarray, path: str):
    cv2.imwrite(path, image)

class YoloDetector:
    """
    YOLO目标检测器类
    
    基于Ultralytics YOLO模型的目标检测器，支持实时目标检测和可视化。
    可以检测图像中的目标，并返回检测框、置信度和类别信息。
    
    Attributes:
        model: YOLO模型实例
        threshold: 置信度阈值，用于过滤低置信度的检测结果
    """
    
    def __init__(self, model_path: str , threshold: float = 0.25):
        """
        初始化YOLO检测器
        
        Args:
            model_path (str): YOLO模型文件的路径
            threshold (float, optional): 置信度阈值，默认为0.25
        """
        self.model = YOLO(model_path)
        self.threshold = threshold

    def detect(self, image_or_path: Union[str, np.ndarray], target_class: Optional[str] = None) -> Tuple[List[Dict], np.ndarray]:
        """
        执行目标检测
        
        对输入图像进行目标检测，返回检测结果和可视化图像。
        支持指定特定类别进行检测，如果未指定则检测所有类别。
        
        Args:
            image_or_path (Union[str, np.ndarray]): 输入图像，可以是图像路径字符串或numpy数组
                                                   numpy数组必须是OpenCV的BGR格式
            target_class (Optional[str], optional): 指定要检测的目标类别，如果为None则检测所有类别
        
        Returns:
            Tuple[List[Dict], np.ndarray]: 
                - 检测结果列表，每个字典包含检测框坐标(xyxy)、置信度(conf)和类别(cls)
                - 可视化图像，包含检测框和标签的标注图像
        
        Note:
            - 检测框坐标格式为 [x1, y1, x2, y2]，其中(x1,y1)为左上角，(x2,y2)为右下角
            - 只有置信度超过阈值的检测结果才会被返回
        """
        # 处理输入图像
        if isinstance(image_or_path, str):
            # 如果输入是路径字符串，则读取图像
            image = cv2.imread(image_or_path)
        else:
            # 如果输入是numpy数组，则直接使用，必须是opencv的bgr格式
            image = image_or_path

        # 如果指定了目标类别，则设置模型只检测该类别
        if target_class:
            self.model.set_classes([target_class])

        # 执行YOLO检测
        results = self.model.predict(image)

        # 获取检测框和可视化结果
        boxes = results[0].boxes
        vis_img = results[0].plot()  # 获取可视化检测结果

        # 提取有效的检测结果
        valid_boxes = []
        for box in boxes:
            # 只保留置信度超过阈值的检测结果
            if box.conf.item() > self.threshold:
                valid_boxes.append({
                    "xyxy": box.xyxy[0].tolist(),  # 检测框坐标 [x1, y1, x2, y2]
                    "conf": box.conf.item(),        # 置信度
                    "cls": results[0].names[box.cls.item()]  # 类别名称
                })

        return valid_boxes, vis_img
  
    
class SamPredictor:
    """
    SAM（Segment Anything Model）分割预测器类
    
    基于Ultralytics的SAM模型，用于图像分割任务。支持通过边界框（bboxes）或点（points）进行分割预测。
    
    Attributes:
        model: SAMPredictor模型实例
        overrides: 模型配置参数字典
    """
    def __init__(self, model_path: str):
        """
        初始化SAM分割预测器
        
        Args:
            model_path (str): SAM模型文件的路径
        """
        self.overrides = {
            'task': 'segment',    
            'mode': 'predict',    
            # 'imgsz': 1024,      
            'model': model_path,  
            'conf': 0.01,         
            'save': False         
        }
        self.model = SAMPredictor(overrides=self.overrides)

    @staticmethod
    def process_sam_results(results):
        """
        处理SAM模型的分割结果，提取掩码和分割区域中心点。
        
        Args:
            results: SAM模型的输出结果
        
        Returns:
            Tuple[Optional[Tuple[int, int]], Optional[np.ndarray]]:
                - 分割区域的中心点坐标(cx, cy)，如果未检测到则为None
                - 分割掩码（uint8类型，255为前景，0为背景），如果未检测到则为None
        """
        if not results or not results[0].masks:
            return None, None

        # Get first mask (assuming single object segmentation)
        mask = results[0].masks.data[0].cpu().numpy()
        mask = (mask > 0).astype(np.uint8) * 255

        # Find contour and center
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, None

        M = cv2.moments(contours[0])
        if M["m00"] == 0:
            return None, mask

        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return (cx, cy), mask


    def predict(self, image_or_path: Union[str, np.ndarray], bboxes: List[int] = None, points: List[int] = None):
        """
        对输入图像进行分割预测。
        
        支持通过边界框或点进行分割：
        - bboxes: 必须为长度为4的列表[x1, y1, x2, y2]，表示分割区域的左上角和右下角坐标。
        - points: 必须为长度为2的列表[x, y]，表示分割点的坐标。
        
        Args:
            image_or_path (Union[str, np.ndarray]): 输入图像，可以是图像路径字符串或numpy数组（RGB格式）。
            bboxes (List[int], optional): 长度为4的边界框坐标列表[x1, y1, x2, y2]。
            points (List[int], optional): 长度为2的点坐标列表[x, y]。
        
        Returns:
            Tuple[Optional[Tuple[int, int]], Optional[np.ndarray]]:
                - 分割区域的中心点坐标(cx, cy)，如果未检测到则为None
                - 分割掩码（uint8类型，255为前景，0为背景），如果未检测到则为None
        """
        # 必须是rgb格式
        if isinstance(image_or_path, str):
            bgr_img = cv2.imread(image_or_path)
            rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        else:
            rgb_img = image_or_path

        self.model.set_image(rgb_img)

        # 检查points和bboxes的格式
        if points is not None:
            assert isinstance(points, list) and len(points) == 2, "points必须为长度为2的列表[x, y]"
            results = self.model(points=[points], labels=[1]) 
        elif bboxes is not None:
            assert isinstance(bboxes, list) and len(bboxes) == 4, "bboxes必须为长度为4的列表[x1, y1, x2, y2]"
            results = self.model(bboxes=[bboxes])
        else:
            results = self.model()

        center, mask = self.process_sam_results(results)

        return center, mask
    
    