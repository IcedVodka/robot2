"""
图像分割模块

该模块集成了YOLO目标检测和SAM（Segment Anything Model）分割功能，
提供完整的图像分割解决方案。支持自动检测、手动选择等多种分割模式。

主要功能：
- 使用YOLO进行目标检测
- 使用SAM进行精确分割
- 支持多种输入格式（文件路径、numpy数组）
- 提供可视化结果保存
- 支持手动和自动选择目标对象

作者: [作者名]
日期: [日期]
版本: 1.0
"""

import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.models.sam import Predictor as SAMPredictor
from typing import Optional, Tuple, List, Dict, Union
import os


class ImageSegmentation:
    """
    图像分割类，集成YOLO检测和SAM分割功能
    
    该类提供了完整的图像分割解决方案，结合了YOLO的目标检测能力
    和SAM的精确分割能力。支持多种分割模式和输入格式。
    
    属性:
        yolo_model: YOLO模型实例，用于目标检测
        sam_predictor: SAM预测器实例，用于精确分割
        current_image: 当前加载的BGR格式图像
        current_image_rgb: 当前加载的RGB格式图像
    """
    
    def __init__(self, yolo_model_path: str = "/home/gml-cwl/code/Dehao-Zhou/yolov8s-world.pt", 
                 sam_model_path: str = "/home/gml-cwl/code/Dehao-Zhou/sam_b.pt"):
        """
        初始化图像分割器
        
        Args:
            yolo_model_path: YOLO模型文件路径，默认为yolov8s-world.pt
            sam_model_path: SAM模型文件路径，默认为sam_b.pt
            
        Raises:
            FileNotFoundError: 当模型文件不存在时抛出
            RuntimeError: 当模型加载失败时抛出
        """
        # 初始化YOLO模型
        self.yolo_model = YOLO(yolo_model_path)
        
        # 初始化SAM预测器
        self.sam_predictor = self._init_sam_predictor(sam_model_path)
        
        # 初始化图像存储变量
        self.current_image = None  # BGR格式
        self.current_image_rgb = None  # RGB格式
        
    def _init_sam_predictor(self, model_path: str) -> SAMPredictor:
        """
        初始化SAM预测器
        
        Args:
            model_path: SAM模型文件路径
            
        Returns:
            SAMPredictor: 配置好的SAM预测器实例
            
        Raises:
            RuntimeError: 当SAM模型加载失败时抛出
        """
        # 配置SAM预测器参数
        overrides = dict(
            task='segment',  # 任务类型为分割
            mode='predict',  # 预测模式
            model=model_path,  # 模型路径
            conf=0.01,  # 置信度阈值
            save=False  # 不保存中间结果
        )
        return SAMPredictor(overrides=overrides)
    
    def _load_image(self, image_input: Union[str, np.ndarray]) -> np.ndarray:
        """
        加载图像并转换为RGB格式
        
        Args:
            image_input: 图像输入，可以是文件路径或numpy数组
            
        Returns:
            np.ndarray: RGB格式的图像数组
            
        Raises:
            FileNotFoundError: 当图像文件不存在时抛出
            ValueError: 当图像读取失败时抛出
        """
        if isinstance(image_input, str):
            # 输入为文件路径
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image file not found: {image_input}")
            
            # 读取BGR格式图像
            bgr_img = cv2.imread(image_input)
            if bgr_img is None:
                raise ValueError(f"Failed to read image from path: {image_input}")
        else:
            # 输入为numpy数组
            bgr_img = image_input
            
        # 存储当前图像（BGR格式）
        self.current_image = bgr_img
        
        # 转换为RGB格式并存储
        self.current_image_rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        
        return self.current_image_rgb
    
    def detect_objects(self, target_class: Optional[str] = None, 
                      confidence_threshold: float = 0.25) -> Tuple[List[Dict], np.ndarray]:
        """
        使用YOLO检测目标对象
        
        Args:
            target_class: 目标类别名称，如果为None则检测所有类别
            confidence_threshold: 置信度阈值，过滤低置信度的检测结果
            
        Returns:
            Tuple[List[Dict], np.ndarray]: 
                - 检测结果列表，每个元素包含xyxy坐标、置信度和类别
                - 可视化图像，标注了检测框和类别信息
                
        Raises:
            ValueError: 当没有加载图像时抛出
        """
        if self.current_image is None:
            raise ValueError("No image loaded. Call segment() first.")
            
        # 设置目标类别（如果指定）
        if target_class:
            self.yolo_model.set_classes([target_class])
        
        # 执行YOLO检测
        results = self.yolo_model.predict(self.current_image)
        boxes = results[0].boxes
        vis_img = results[0].plot()  # 生成可视化图像
        
        # 提取有效的检测结果
        valid_detections = []
        for box in boxes:
            # 过滤低置信度的检测结果
            if box.conf.item() > confidence_threshold:
                valid_detections.append({
                    "xyxy": box.xyxy[0].tolist(),  # 边界框坐标 [x1, y1, x2, y2]
                    "conf": box.conf.item(),  # 置信度
                    "cls": results[0].names[box.cls.item()]  # 类别名称
                })
        
        return valid_detections, vis_img
    
    def _process_sam_results(self, results) -> Tuple[Optional[Tuple[int, int]], Optional[np.ndarray]]:
        """
        处理SAM分割结果
        
        Args:
            results: SAM预测结果
            
        Returns:
            Tuple[Optional[Tuple[int, int]], Optional[np.ndarray]]:
                - 分割对象的中心点坐标 (x, y)，如果计算失败则为None
                - 分割掩码数组，如果分割失败则为None
        """
        # 检查是否有有效的分割结果
        if not results or not results[0].masks:
            return None, None
            
        # 获取第一个掩码
        mask = results[0].masks.data[0].cpu().numpy()
        # 将掩码转换为二值图像 (0 或 255)
        mask = (mask > 0).astype(np.uint8) * 255
        
        # 计算轮廓和中心点
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, mask
            
        # 计算轮廓的矩
        M = cv2.moments(contours[0])
        if M["m00"] == 0:
            return None, mask
            
        # 计算中心点坐标
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        
        return (cx, cy), mask
    
    def _manual_selection(self, vis_img: np.ndarray) -> Tuple[int, int]:
        """
        手动选择目标对象
        
        Args:
            vis_img: 可视化图像，用于显示给用户选择
            
        Returns:
            Tuple[int, int]: 用户选择的点坐标 (x, y)
            
        Raises:
            ValueError: 当用户没有做出选择时抛出
        """
        print("No detections - click on target object")
        cv2.imshow('Select Object', vis_img)
        point = []
        
        def click_handler(event, x, y, flags, param):
            """鼠标点击事件处理函数"""
            if event == cv2.EVENT_LBUTTONDOWN:
                point.extend([x, y])
                cv2.destroyAllWindows()
        
        # 设置鼠标回调函数
        cv2.setMouseCallback('Select Object', click_handler)
        cv2.waitKey(0)  # 等待用户点击
        
        if len(point) != 2:
            raise ValueError("No selection made")
            
        return tuple(point)
    
    def segment(self, image_input: Union[str, np.ndarray], 
                target_class: Optional[str] = None,
                auto_select: bool = True,
                output_mask: str = 'mask1.png',
                save_visualization: bool = True,
                manual_point: Optional[Tuple[int, int]] = None) -> Optional[np.ndarray]:
        """
        执行图像分割的主方法
        
        Args:
            image_input: 图像输入，可以是文件路径或numpy数组
            target_class: 目标类别名称，如果为None则检测所有类别
            auto_select: 是否自动选择最高置信度的检测结果
            output_mask: 输出掩码文件名
            save_visualization: 是否保存检测可视化结果
            manual_point: 手动选择的点坐标 (x, y)，如果提供则跳过自动检测
            
        Returns:
            Optional[np.ndarray]: 分割掩码数组，失败时返回None
            
        Raises:
            FileNotFoundError: 当图像文件不存在时抛出
            ValueError: 当图像读取失败或分割失败时抛出
        """
        # 加载图像
        self._load_image(image_input)
        
        # 设置SAM预测器的输入图像
        self.sam_predictor.set_image(self.current_image_rgb)
        
        # 执行目标检测
        detections, vis_img = self.detect_objects(target_class)
        
        # 保存可视化结果（如果需要）
        if save_visualization:
            cv2.imwrite('detection_visualization.jpg', vis_img)
        
        # 执行分割
        center, mask = None, None
        
        if manual_point is not None:
            # 使用外部提供的点进行分割
            results = self.sam_predictor(points=[manual_point], labels=[1])
            center, mask = self._process_sam_results(results)
            print(f"Using provided point: {manual_point}")
            
        elif detections and auto_select:
            # 自动选择最高置信度的检测结果
            best_detection = max(detections, key=lambda x: x["conf"])
            results = self.sam_predictor(bboxes=[best_detection["xyxy"]])
            center, mask = self._process_sam_results(results)
            print(f"Auto-selected {best_detection['cls']} with confidence {best_detection['conf']:.2f}")
            
        else:
            # 手动选择目标对象
            point = self._manual_selection(vis_img)
            results = self.sam_predictor(points=[point], labels=[1])
            center, mask = self._process_sam_results(results)
        
        # 保存分割掩码
        if mask is not None:
            cv2.imwrite(output_mask, mask, [cv2.IMWRITE_PNG_BILEVEL, 1])
            print(f"Segmentation saved to {output_mask}")
        else:
            print("[WARNING] Could not generate mask")
        
        return mask
    
    def get_segmentation_center(self) -> Optional[Tuple[int, int]]:
        """
        获取分割对象的中心点
        
        Returns:
            Optional[Tuple[int, int]]: 分割对象的中心点坐标 (x, y)，
                                     如果无法获取则返回None
        """
        if self.current_image is None:
            return None
            
        # 重新执行分割以获取中心点
        detections, _ = self.detect_objects()
        if detections:
            # 选择最高置信度的检测结果
            best_detection = max(detections, key=lambda x: x["conf"])
            results = self.sam_predictor(bboxes=[best_detection["xyxy"]])
            center, _ = self._process_sam_results(results)
            return center
        return None


def main():
    """
    示例用法函数
    
    演示如何使用ImageSegmentation类进行图像分割
    """
    # 创建分割器实例
    segmenter = ImageSegmentation()
    
    # 执行分割
    image_path = '/home/gml-cwl/code/Dehao-Zhou/传统抓取全流程代码/fruit.jpg'
    mask = segmenter.segment(image_path)
    
    # 处理分割结果
    if mask is not None:
        print(f"Segmentation result mask shape: {mask.shape}")
        center = segmenter.get_segmentation_center()
        if center:
            print(f"Object center: {center}")
    else:
        print("Segmentation failed")


if __name__ == '__main__':
    main() 