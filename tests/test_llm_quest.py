import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grasp_task2.llm_quest import VisionAPI, ImageInput


def test_prescription_recognition():
    """测试处方单识别功能"""
    test_image = "data/cam_capture/realsense_color_327122078945_20250813_112112.jpg"
    
    try:
        # 创建API实例
        api = VisionAPI()
        
        # 创建图像输入
        image_input = ImageInput(image_path=test_image)
        
        # 测试处方单识别
        print("正在识别处方单中的药品...")
        medicines = api.extract_prescription_medicines(image_input)
        print(f"识别到的药品：{medicines}")
        
    except Exception as e:
        print(f"测试过程中出现错误：{str(e)}")


def test_medicine_box_detection():
    """测试药品盒检测功能"""
    test_image = "/home/s402/yd/robot2/logs/20250813_133927_left_rgb.jpg"
    
    try:
        # 创建API实例
        api = VisionAPI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        
        # 创建图像输入
        image_input = ImageInput(image_path=test_image)
        
        # 测试药品盒检测
        medicine_name = "硫酸氢氯吡格雷片"
        print(f"正在检测图片中的 '{medicine_name}'...")
        box_coords = api.detect_medicine_box(image_input, medicine_name)
        print(f"检测结果：{box_coords} [x1, y1, x2, y2]")
        
    except Exception as e:
        print(f"测试过程中出现错误：{str(e)}")


if __name__ == "__main__":
    # 分别运行两个测试
    print("=== 测试处方单识别 ===")
    test_prescription_recognition()
    
    print("\n=== 测试药品盒检测 ===")
    test_medicine_box_detection() 