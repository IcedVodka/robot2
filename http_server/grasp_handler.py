import time
import os
import sys

# 确保项目根目录在 sys.path 中（支持从 http_server 目录直接运行）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from grasp_task2.grasp_task import GraspTask


class GraspHandler:
    def __init__(self):
        """初始化抓取处理器"""
        self.grasp_task = GraspTask()
     

    def process_prescription_recognition(self):
        """处方识别
        Returns:
            list: 药品列表，例如 ["药品A", "药品B"]            
        """
        # 调用grasp_task的处方识别方法
        self.grasp_task.prescription_recognition()

        return self.grasp_task.medicine_list


    def process_grasp(self, medicines):
        """执行抓取
        Args:
            medicines (list): 要抓取的药品列表
        Returns:
            list: 更新后的药品列表
        """

        self.grasp_task.shelf_grasp()
        return self.grasp_task.medicine_list


        # return medicines[1:] if medicines and len(medicines) > 0 else None
    
    def place_medicine_basket(self):
        """放置药品篮子
        """

        self.grasp_task.place_medicine_basket()      

        return True