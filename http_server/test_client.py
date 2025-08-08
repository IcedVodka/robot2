import requests
import time

# 服务器地址
BASE_URL = "http://localhost:5000"

def test_prescription_recognition():
    """测试处方识别接口"""
    print("\n=== 测试处方识别 ===")
    response = requests.post(f"{BASE_URL}/prescription_recognition")
    if response.status_code == 200:
        task_id = response.json()["task_id"]
        print(f"开始处方识别任务，任务ID: {task_id}")
        
        # 轮询任务状态
        while True:
            status_response = requests.get(f"{BASE_URL}/task_status/{task_id}")
            status = status_response.json()["status"]
            print(f"任务状态: {status}")
            if status == "complete":
                break
            time.sleep(2)
    else:
        print(f"处方识别请求失败: {response.status_code}")

def test_get_prescription_list():
    """测试获取处方列表接口"""
    print("\n=== 测试获取处方列表 ===")
    response = requests.get(f"{BASE_URL}/prescription_list")
    if response.status_code == 200:
        prescriptions = response.json()["prescriptions"]
        print("处方列表:")
        for prescription in prescriptions:
            print(f"- {prescription}")
    else:
        print(f"获取处方列表失败: {response.status_code}")

def test_start_grasp():
    """测试开始抓取接口"""
    print("\n=== 测试开始抓取 ===")
    response = requests.post(f"{BASE_URL}/start_grasp")
    if response.status_code == 200:
        task_id = response.json()["task_id"]
        print(f"开始抓取任务，任务ID: {task_id}")
        
        # 轮询任务状态
        while True:
            status_response = requests.get(f"{BASE_URL}/task_status/{task_id}")
            status = status_response.json()["status"]
            print(f"任务状态: {status}")
            if status == "complete":
                break
            time.sleep(2)
    else:
        print(f"开始抓取请求失败: {response.status_code}")

def main():
    """运行所有测试"""
     # 测试处方识别
    test_prescription_recognition()
    
    # 测试获取处方列表
    test_get_prescription_list()
    
    # 测试开始抓取
    test_start_grasp()

    # 测试获取抓取结果
    test_get_prescription_list()

if __name__ == "__main__":
    main() 