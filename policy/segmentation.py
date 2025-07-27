import cv2
import numpy as np
import os
from typing import Optional, Tuple, List, Dict, Union
from policy.models.yolo_model import YoloModel
from policy.models.sam_model import SamModel

class ImageSegmentationPipeline:
    """
    图像分割业务主流程调度类
    只负责业务调度，不处理底层细节
    """
    def __init__(self, yolo_model_path: str, sam_model_path: str):
        self.yolo = YoloModel(yolo_model_path)
        self.sam = SamModel(sam_model_path)
        self.current_image = None  # BGR格式
        self.current_image_rgb = None  # RGB格式

    def _load_image(self, image_input: Union[str, np.ndarray]) -> np.ndarray:
        """
        加载图像并转换为RGB格式
        """
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image file not found: {image_input}")
            bgr_img = cv2.imread(image_input)
            if bgr_img is None:
                raise ValueError(f"Failed to read image from path: {image_input}")
        else:
            bgr_img = image_input
        self.current_image = bgr_img
        self.current_image_rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        return self.current_image_rgb

    def _process_sam_results(self, results) -> Tuple[Optional[Tuple[int, int]], Optional[np.ndarray]]:
        """
        处理SAM分割结果，返回中心点和掩码
        """
        if not results or not hasattr(results[0], 'masks') or results[0].masks is None:
            return None, None
        mask = results[0].masks.data[0].cpu().numpy()
        mask = (mask > 0).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, mask
        M = cv2.moments(contours[0])
        if M["m00"] == 0:
            return None, mask
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return (cx, cy), mask

    def segment(self, image_input: Union[str, np.ndarray],
                target_class: Optional[str] = None,
                auto_select: bool = True,
                output_mask: str = 'mask1.png',
                save_visualization: bool = True,
                manual_point: Optional[Tuple[int, int]] = None) -> Optional[np.ndarray]:
        """
        主业务流程：图像分割
        """
        # 1. 加载图像
        self._load_image(image_input)
        self.sam.set_image(self.current_image_rgb)
        # 2. 检测目标
        detections = self.yolo.predict(self.current_image, target_class)
        vis_img = self.yolo.plot(self.current_image)
        if save_visualization:
            cv2.imwrite('detection_visualization.jpg', vis_img)
        # 3. 分割
        center, mask = None, None
        if manual_point is not None:
            results = self.sam.predict_by_point(manual_point)
            center, mask = self._process_sam_results(results)
            print(f"[INFO] 使用手动点: {manual_point}")
        elif detections and auto_select:
            best = max(detections, key=lambda x: x["conf"])
            results = self.sam.predict_by_bbox(best["xyxy"])
            center, mask = self._process_sam_results(results)
            print(f"[INFO] 自动选择 {best['cls']} 置信度 {best['conf']:.2f}")
        else:
            print("[WARNING] 未检测到目标，需手动指定点")
            # 这里可扩展为GUI点选，当前直接返回None
            return None
        # 4. 保存掩码
        if mask is not None:
            cv2.imwrite(output_mask, mask, [cv2.IMWRITE_PNG_BILEVEL, 1])
            print(f"[INFO] 分割掩码已保存: {output_mask}")
        else:
            print("[WARNING] 掩码生成失败")
        return mask

    def get_segmentation_center(self) -> Optional[Tuple[int, int]]:
        """
        获取分割对象的中心点
        """
        if self.current_image is None:
            return None
        detections = self.yolo.predict(self.current_image)
        if detections:
            best = max(detections, key=lambda x: x["conf"])
            results = self.sam.predict_by_bbox(best["xyxy"])
            center, _ = self._process_sam_results(results)
            return center
        return None

if __name__ == '__main__':
    # 示例用法
    yolo_path = 'your_yolo_model.pt'  # 替换为实际模型路径
    sam_path = 'your_sam_model.pt'    # 替换为实际模型路径
    image_path = 'test.jpg'           # 替换为实际图片路径
    pipeline = ImageSegmentationPipeline(yolo_path, sam_path)
    mask = pipeline.segment(image_path)
    center = pipeline.get_segmentation_center()
    print('分割中心点:', center)
