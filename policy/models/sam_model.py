import numpy as np
from ultralytics.models.sam import Predictor as SAMPredictor
from typing import Optional, Tuple, List

class SamModel:
    def __init__(self, model_path: str):
        overrides = dict(
            task='segment',
            mode='predict',
            model=model_path,
            conf=0.01,
            save=False
        )
        self.predictor = SAMPredictor(overrides=overrides)

    def set_image(self, image: np.ndarray):
        self.predictor.set_image(image)

    def predict_by_point(self, point: Tuple[int, int]) -> List:
        return self.predictor(points=[point], labels=[1])

    def predict_by_bbox(self, bbox: List[float]) -> List:
        return self.predictor(bboxes=[bbox]) 