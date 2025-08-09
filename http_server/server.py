from flask import Flask, jsonify
import threading
import uuid
import time
import os
from grasp_handler import GraspHandler

app = Flask(__name__)

# 全局变量
tasks = {}  # 存储任务状态
MEDICINES_FILE = "medicines.txt"  # 药品列表文件
grasp_handler = GraspHandler()  # 抓取处理器实例

# 任务状态
TASK_INCOMPLETE = "incomplete"
TASK_COMPLETE = "complete"

def read_medicines():
    """读取药品列表"""
    if not os.path.exists(MEDICINES_FILE):
        return []
    with open(MEDICINES_FILE, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def write_medicines(medicines):
    """写入药品列表"""
    with open(MEDICINES_FILE, 'w') as f:
        for medicine in medicines:
            f.write(f"{medicine}\n")

@app.route('/prescription_recognition', methods=['POST'])
def start_prescription_recognition():
    task_id = str(uuid.uuid4())
    tasks[task_id] = TASK_INCOMPLETE
    
    def run_task():
        medicines = grasp_handler.process_prescription_recognition()
        if medicines:  # 只有在识别成功时才写入文件
            write_medicines(medicines)
        tasks[task_id] = TASK_COMPLETE
    
    threading.Thread(target=run_task).start()
    return jsonify({"task_id": task_id})

@app.route('/place_medicine_basket', methods=['POST'])
def place_medicine_basket():
    """放置药品篮子任务，返回 task_id，完成后清空药品列表文件"""
    task_id = str(uuid.uuid4())
    tasks[task_id] = TASK_INCOMPLETE

    def run_task():
        try:
            grasp_handler.place_medicine_basket()
        finally:
            # 任务完成后清空药品列表
            write_medicines([])
            tasks[task_id] = TASK_COMPLETE

    threading.Thread(target=run_task).start()
    return jsonify({"task_id": task_id})

@app.route('/prescription_list', methods=['GET'])
def get_prescription_list():
    medicines = read_medicines()
    return jsonify({"prescriptions": medicines})

@app.route('/start_grasp', methods=['POST'])
def start_grasp():
    medicines = read_medicines()
    if not medicines:
        return jsonify({"error": "No medicines available"}), 400
    
    task_id = str(uuid.uuid4())
    tasks[task_id] = TASK_INCOMPLETE
    
    def run_task():
        new_medicines = grasp_handler.process_grasp(medicines)
        if new_medicines is not None:  # 只有在抓取成功时才更新文件
            write_medicines(new_medicines)
        tasks[task_id] = TASK_COMPLETE
    
    threading.Thread(target=run_task).start()
    return jsonify({"task_id": task_id})

@app.route('/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({"status": tasks[task_id]})

if __name__ == '__main__':
    # 确保文件存在
    if not os.path.exists(MEDICINES_FILE):
        open(MEDICINES_FILE, 'a').close()
    app.run(host='0.0.0.0', port=5000)
