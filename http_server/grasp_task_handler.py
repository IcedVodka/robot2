import json
import time
from threading import Lock

class GraspTask:
    def __init__(self, shared_file_path):
        """
        初始化抓取任务处理器
        
        Args:
            shared_file_path (str): 共享文件的路径，用于存储待抓取的药品列表
        """
        self.shared_file_path = shared_file_path
        self.file_lock = Lock()
        
    def recognize_prescription(self):
        """
        处方识别方法
        
        Returns:
            list: 识别出的药品列表，每个药品为一个字典，包含name和status字段
                 例如：[{"name": "阿司匹林", "status": "pending"}, ...]
        """
        print("开始处方识别...")
        time.sleep(5)  # 模拟耗时操作
        
        # 这里应该是实际的处方识别逻辑
        medicine_list = [
            {"name": "阿司匹林", "status": "pending"},
            {"name": "布洛芬", "status": "pending"},
            {"name": "维生素C", "status": "pending"}
        ]
        
        # 将结果写入共享文件
        self._write_shared_file({"medicines": medicine_list})
        return medicine_list
        
    def grasp_medicines(self, medicines_to_grasp=None):
        """
        抓取药品方法。如果指定了具体药品列表，则抓取指定药品；
        如果未指定药品列表，则抓取共享文件中的所有待抓取药品。
        
        Args:
            medicines_to_grasp (list, optional): 要抓取的药品列表，每个药品应包含name字段。
                                               如果为None，则抓取所有待抓取的药品。
                                               默认为None。
        
        Returns:
            list: 成功抓取的药品列表
            
        Raises:
            ValueError: 当指定的药品不在待抓取列表中时抛出
            ValueError: 当没有任何待抓取的药品时抛出
        """
        # 读取当前待抓取的药品列表
        data = self._read_shared_file()
        current_medicines = data.get("medicines", [])
        
        # 如果当前没有待抓取的药品，直接抛出异常
        if not current_medicines:
            raise ValueError("没有待抓取的药品")
            
        # 如果未指定要抓取的药品，则抓取所有待抓取的药品
        if medicines_to_grasp is None:
            medicines_to_grasp = current_medicines
            print(f"准备抓取所有药品: {[m['name'] for m in medicines_to_grasp]}")
        else:
            print(f"准备抓取指定药品: {[m['name'] for m in medicines_to_grasp]}")
            # 验证要抓取的药品是否在待抓取列表中
            medicine_names_to_grasp = {m['name'] for m in medicines_to_grasp}
            available_medicines = {m['name'] for m in current_medicines}
            
            if not medicine_names_to_grasp.issubset(available_medicines):
                invalid_medicines = medicine_names_to_grasp - available_medicines
                raise ValueError(f"以下药品不在待抓取列表中: {invalid_medicines}")
            
        time.sleep(10)  # 模拟耗时的抓药过程
        
        # 实际的抓药逻辑应该在这里
        # ...
        
        # 从待抓取列表中移除已抓取的药品
        medicine_names_to_grasp = {m['name'] for m in medicines_to_grasp}
        updated_medicines = [
            m for m in current_medicines 
            if m['name'] not in medicine_names_to_grasp
        ]
        
        # 更新共享文件
        self._write_shared_file({"medicines": updated_medicines})
        
        # 返回成功抓取的药品
        return medicines_to_grasp
        
    def _read_shared_file(self):
        """
        读取共享文件中的数据
        
        Returns:
            dict: 包含medicines字段的字典，如果文件不存在或格式错误，返回空列表
                 例如：{"medicines": [{"name": "阿司匹林", "status": "pending"}, ...]}
        """
        try:
            with self.file_lock:
                with open(self.shared_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"medicines": []}
            
    def _write_shared_file(self, data):
        """
        将数据写入共享文件
        
        Args:
            data (dict): 要写入的数据，必须包含medicines字段
                        例如：{"medicines": [{"name": "阿司匹林", "status": "pending"}, ...]}
        """
        with self.file_lock:
            with open(self.shared_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

# 创建全局实例
grasp_task_handler = GraspTask("shared_results.txt") 