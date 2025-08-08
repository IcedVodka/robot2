import cv2
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from policy.segmentation import YoloDetector, SamPredictor

# 路径配置
image_path = "data/test_images/realsense_color_327122072195_20250728_172254.jpg"
output_dir = "data/outputs"
os.makedirs(output_dir, exist_ok=True)

# 模型权重路径（请替换为你自己的模型文件路径）
yolo_model_path = "/home/gml-cwl/code/robot2/assets/weights/yolov8s-world.pt"
sam_model_path = "assets\sam_l.pt"

def test_yolo_sam_box():
    """测试YOLO检测 + SAM box模式分割"""
    print("=== 测试YOLO检测 + SAM box模式分割 ===")
    
    # 1. 用YOLO检测，取置信度最高的box
    yolo = YoloDetector(yolo_model_path)
    boxes, vis_img = yolo.detect(image_path)
    if not boxes:
        print("未检测到目标")
        return False
    
    best_box = max(boxes, key=lambda x: x["conf"])["xyxy"]
    print(f"检测到最佳目标框: {best_box}")

    # 2. 用SAM分割（box模式）
    sam = SamPredictor(sam_model_path)
    center, mask = sam.predict(image_path, bboxes=best_box)
    if mask is not None:
        mask_path = os.path.join(output_dir, "mask_by_box.png")
        cv2.imwrite(mask_path, mask)
        print(f"Box模式分割结果已保存: {mask_path}")
        return True
    else:
        print("Box模式未分割出有效区域")
        return False

def test_sam_point():
    """测试SAM点选模式分割"""
    print("=== 测试SAM点选模式分割 ===")
    
    # 用OpenCV窗口让用户点选一个点
    clicked_point = []
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            clicked_point.clear()
            clicked_point.extend([x, y])
            cv2.destroyAllWindows()

    img = cv2.imread(image_path)
    # window_name不能出现中文
    window_name = "SAM Test"
    cv2.imshow(window_name, img)
    cv2.setMouseCallback(window_name, mouse_callback)
    cv2.waitKey(0)

    if clicked_point:
        print(f"选择的点: {clicked_point}")
        sam = SamPredictor(sam_model_path)
        # 将img转换为rgb格式
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        center, mask = sam.predict(img, points=clicked_point)
        # 或者直接用image_path
        # center, mask = sam.predict(image_path, points=clicked_point)
  
        if mask is not None:
            mask_path = os.path.join(output_dir, "mask_by_point.png")
            cv2.imwrite(mask_path, mask)
            print(f"点选模式分割结果已保存: {mask_path}")
            return True
        else:
            print("点选模式未分割出有效区域")
            return False
    else:
        print("未点选任何点")
        return False

def main():
    """主函数 - 选择测试模式"""
    print("SAM测试程序")
    print("1. YOLO检测 + SAM box模式分割")
    print("2. SAM点选模式分割")
    print("3. 运行所有测试")
    
    choice = input("请选择测试模式 (1/2/3): ").strip()
    
    if choice == "1":
        test_yolo_sam_box()
    elif choice == "2":
        test_sam_point()
    elif choice == "3":
        test_yolo_sam_box()
        print("\n" + "="*50 + "\n")
        test_sam_point()
    else:
        print("无效选择，退出程序")

if __name__ == "__main__":
    main()