import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_quest import VisionAPI, ImageInput


def test_prescription_recognition():
    """测试处方单识别功能"""
    test_image = "../data/test_images/camera_12_20250730_165750.jpg"
    
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
    test_image = "/tmp/tmpb980wlln.jpg"
    
    try:
        # 创建API实例
        api = VisionAPI()
        
        # 创建图像输入
        image_input = ImageInput(image_path=test_image)
        
        # 测试药品盒检测
        medicine_name = "口炎清颗粒"
        print(f"正在检测图片中的 '{medicine_name}'...")
        x, y = api.detect_medicine_box(image_input, medicine_name)
        print(f"检测结果：[{x}, {y}]")
        
    except Exception as e:
        print(f"测试过程中出现错误：{str(e)}")


if __name__ == "__main__":
    # 分别运行两个测试
    print("=== 测试处方单识别 ===")
    test_prescription_recognition()
    
    print("\n=== 测试药品盒检测 ===")
    test_medicine_box_detection() 