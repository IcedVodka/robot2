import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grasp_task2.llm_quest import VisionAPI, ImageInput


def test_prescription_recognition():
    """测试处方单识别功能"""
    test_image = "/home/s402/yd/robot2/screenshots/left_camera_20250815_141012.jpg"
    
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
    test_image = "/home/s402/yd/robot2/logs/20250815_153449_right_rgb.jpg"
    import cv2
    # 创建API实例
    api = VisionAPI()
    
    # 创建图像输入
    image_input = ImageInput(image_path=test_image)
    
    # 测试药品盒检测
    medicine_name = "维c银翘片"
    print(f"正在检测图片中的 '{medicine_name}'...")
    box_coords = api.detect_medicine_box_direct(image_input, medicine_name)
    print(f"检测结果：{box_coords} [x1, y1, x2, y2]")


    image = cv2.imread(test_image)   
    x1, y1, x2, y2 = box_coords[0], box_coords[1], box_coords[2], box_coords[3]
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # 添加标签
    cv2.putText(image, "维c银翘片", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2) 
    cv2.imshow("Image", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
   


if __name__ == "__main__":
    # 分别运行两个测试
    print("=== 测试处方单识别 ===")
    test_prescription_recognition()
    
    print("\n=== 测试药品盒检测 ===")
    test_medicine_box_detection() 