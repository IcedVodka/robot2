import requests
import time
import json

BASE_URL = "http://localhost:5000"

def test_prescription_recognition():
    """测试处方识别流程"""
    print("\n=== 测试处方识别 ===")
    
    # 发起处方识别请求
    response = requests.post(f"{BASE_URL}/process/1")
    if response.status_code != 200:
        print("处方识别请求失败:", response.json())
        return
    
    task_id = response.json()["task_id"]
    print(f"任务ID: {task_id}")
    
    # 轮询任务状态
    while True:
        response = requests.get(f"{BASE_URL}/task/{task_id}")
        task_status = response.json()
        print(f"任务状态: {task_status['status']}")
        
        if task_status["status"] in ["completed", "failed"]:
            if task_status["status"] == "completed":
                print("识别结果:", json.dumps(task_status["result"], ensure_ascii=False, indent=2))
            else:
                print("任务失败:", task_status.get("error"))
            break
            
        time.sleep(1)
    
    # 删除任务
    response = requests.delete(f"{BASE_URL}/task/{task_id}")
    print("删除任务结果:", response.json())

def test_medicine_grasping():
    """测试药品抓取流程"""
    print("\n=== 测试药品抓取 ===")
    
    # 首先获取待抓取的药品列表
    response = requests.get(f"{BASE_URL}/pending_medicines")
    if response.status_code != 200:
        print("获取待抓取药品列表失败:", response.json())
        return
        
    medicines = response.json()["medicines"]
    if not medicines:
        print("没有待抓取的药品")
        return
        
    print("待抓取药品:", json.dumps(medicines, ensure_ascii=False, indent=2))
    
    # 发起抓取请求
    data = {"medicines": medicines[:1]}  # 只抓取第一个药品作为测试
    response = requests.post(f"{BASE_URL}/process/2", json=data)
    if response.status_code != 200:
        print("抓取请求失败:", response.json())
        return
        
    task_id = response.json()["task_id"]
    print(f"任务ID: {task_id}")
    
    # 轮询任务状态
    while True:
        response = requests.get(f"{BASE_URL}/task/{task_id}")
        task_status = response.json()
        print(f"任务状态: {task_status['status']}")
        
        if task_status["status"] in ["completed", "failed"]:
            if task_status["status"] == "completed":
                print("抓取结果:", json.dumps(task_status["result"], ensure_ascii=False, indent=2))
            else:
                print("任务失败:", task_status.get("error"))
            break
            
        time.sleep(1)
    
    # 删除任务
    response = requests.delete(f"{BASE_URL}/task/{task_id}")
    print("删除任务结果:", response.json())

if __name__ == "__main__":
    # 测试处方识别
    test_prescription_recognition()
    
    # 测试药品抓取
    test_medicine_grasping() 