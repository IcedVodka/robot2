from flask import Flask, jsonify, request
import json
import time
import os
from threading import Lock, Thread
from uuid import uuid4
from queue import Queue
import threading
from grasp_task_handler import grasp_task_handler

# 初始化Flask应用
app = Flask(__name__)
# 定义共享文件路径，用于存储药品列表
SHARED_FILE = "shared_results.txt"
# 文件锁，用于同步文件读写操作
file_lock = Lock()

# 存储所有任务的字典，键为任务ID，值为任务详情
tasks = {}
# 任务队列，用于异步处理任务
task_queue = Queue()

class TaskStatus:
    """任务状态枚举"""
    PENDING = "pending"      # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"         # 失败

def process_task_queue():
    """
    后台任务处理线程
    持续监听任务队列，处理新的任务请求
    支持两种任务类型：
    1. 处方识别
    2. 药品抓取
    """
    while True:
        if not task_queue.empty():
            task_id, action, medicines_to_grasp = task_queue.get()
            try:
                if action == '1':
                    # 处方识别任务
                    tasks[task_id]['status'] = TaskStatus.PROCESSING
                    medicine_list = grasp_task_handler.recognize_prescription()
                    tasks[task_id]['status'] = TaskStatus.COMPLETED
                    tasks[task_id]['result'] = medicine_list
                    
                elif action == '2':
                    # 药品抓取任务
                    tasks[task_id]['status'] = TaskStatus.PROCESSING
                    medicines = grasp_task_handler.grasp_medicines(medicines_to_grasp)
                    tasks[task_id]['status'] = TaskStatus.COMPLETED
                    tasks[task_id]['result'] = medicines
                    
            except Exception as e:
                tasks[task_id]['status'] = TaskStatus.FAILED
                tasks[task_id]['error'] = str(e)
            
            task_queue.task_done()

def read_shared_file():
    """
    读取共享文件中的数据
    Returns:
        dict: 包含medicines列表的字典，如果文件不存在则返回空列表
    """
    try:
        with file_lock:
            with open(SHARED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"medicines": []}

def write_shared_file(data):
    """
    将数据写入共享文件
    Args:
        data (dict): 要写入的数据，必须包含medicines字段
    """
    with file_lock:
        with open(SHARED_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/process/<action>', methods=['POST'])
def process_action(action):
    """
    处理任务请求的端点
    Args:
        action (str): 任务类型
            '1': 处方识别
            '2': 药品抓取
    Returns:
        JSON: 包含任务ID的响应
    """
    if action not in ['1', '2']:
        return jsonify({"status": "error", "message": "无效的操作"}), 400
    
    # 创建新任务并分配唯一ID
    task_id = str(uuid4())
    tasks[task_id] = {
        'status': TaskStatus.PENDING,
        'action': action,
        'created_at': time.time()
    }
    
    # 对于抓取操作，从请求体中获取要抓取的药品列表
    medicines_to_grasp = None
    if action == '2':
        data = request.get_json()
        if not data or 'medicines' not in data:
            return jsonify({"status": "error", "message": "请指定要抓取的药品列表"}), 400
        medicines_to_grasp = data['medicines']
    
    # 将任务添加到队列中等待处理
    task_queue.put((task_id, action, medicines_to_grasp))
    
    return jsonify({
        "status": "accepted",
        "message": "任务已接受",
        "task_id": task_id
    })

@app.route('/pending_medicines', methods=['GET'])
def get_pending_medicines():
    """
    获取当前待抓取的药品列表
    Returns:
        JSON: 包含待抓取药品列表的响应
    """
    try:
        data = grasp_task_handler._read_shared_file()
        return jsonify({
            "status": "success",
            "medicines": data.get("medicines", [])
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    获取指定任务的状态
    Args:
        task_id (str): 任务ID
    Returns:
        JSON: 包含任务状态和结果的响应
    """
    if task_id not in tasks:
        return jsonify({"status": "error", "message": "任务不存在"}), 404
    
    task = tasks[task_id]
    response = {
        "status": task['status'],
        "action": task['action']
    }
    
    if task['status'] == TaskStatus.COMPLETED:
        response['result'] = task['result']
    elif task['status'] == TaskStatus.FAILED:
        response['error'] = task.get('error', '未知错误')
    
    return jsonify(response)

@app.route('/task/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """
    删除指定的任务
    Args:
        task_id (str): 任务ID
    Returns:
        JSON: 删除操作的结果
    """
    if task_id not in tasks:
        return jsonify({"status": "error", "message": "任务不存在"}), 404
    
    task = tasks[task_id]
    if task['status'] not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        return jsonify({
            "status": "error", 
            "message": "只能删除已完成或失败的任务"
        }), 400
    
    del tasks[task_id]
    return jsonify({
        "status": "success",
        "message": "任务已删除"
    })

if __name__ == '__main__':
    # 启动任务处理线程
    task_thread = Thread(target=process_task_queue, daemon=True)
    task_thread.start()
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000)