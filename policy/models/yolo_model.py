import numpy as np
from ultralytics import YOLO
from typing import Optional, List, Dict

class YoloModel:
    def __init__(self, model_path: str):
        self.model = YOLO(model_path)

    def predict(self, image: np.ndarray, target_class: Optional[str] = None, confidence_threshold: float = 0.25) -> List[Dict]:
        if target_class:
            self.model.set_classes([target_class])
        results = self.model.predict(image)
        boxes = results[0].boxes
        valid_detections = []
        for box in boxes:
            if box.conf.item() > confidence_threshold:
                valid_detections.append({
                    "xyxy": box.xyxy[0].tolist(),
                    "conf": box.conf.item(),
                    "cls": results[0].names[box.cls.item()]
                })
        return valid_detections

    def plot(self, image: np.ndarray) -> np.ndarray:
        results = self.model.predict(image)
        return results[0].plot() 