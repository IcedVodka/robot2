import cv2
from typing import Callable, Optional

class WindowManager:
    def __init__(self):
        self._callbacks = {}

    def show(self, window_name: str, image):
        cv2.imshow(window_name, image)

    def close(self, window_name: str):
        cv2.destroyWindow(window_name)

    def close_all(self):
        cv2.destroyAllWindows()

    def set_mouse_callback(self, window_name: str, callback: Callable):
        cv2.setMouseCallback(window_name, callback)
        self._callbacks[window_name] = callback

    def wait_key(self, delay: int = 0) -> int:
        return cv2.waitKey(delay)

# 单例实例，方便直接导入使用
window_manager = WindowManager() 