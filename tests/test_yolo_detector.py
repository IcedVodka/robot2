import sys
import os
import cv2
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from policy.segmentation import YoloDetector, save_image

# 请将此处的模型路径替换为你本地的YOLO模型权重文件路径
MODEL_PATH = '/home/gml-cwl/code/robot2/assets/weights/yolov8s-world.pt'  # 示例：'yolov8n.pt'，需确保模型文件存在

IMAGE_DIR = os.path.join(os.path.dirname(__file__), '../data/test_images')
IMAGE_LIST = ['fang.jpg', 'fruit.jpg']

def test_batch_detection():
    """原有的批量测试方法"""
    detector = YoloDetector(MODEL_PATH, threshold=0.25)
    for img_name in IMAGE_LIST:
        img_path = os.path.join(IMAGE_DIR, img_name)
        print(f'检测图片: {img_path}')
        boxes, vis_img = detector.detect(img_path)
        print(f'检测到 {len(boxes)} 个目标')
        for i, box in enumerate(boxes):
            print(f'  目标{i+1}: 类别={box["cls"]}, 置信度={box["conf"]:.2f}, 坐标={box["xyxy"]}')
        # 可选：保存可视化结果
        out_path = os.path.join(IMAGE_DIR, f"result_{img_name}")
        save_image(vis_img, out_path)
        print(f'可视化结果已保存到: {out_path}\n')

def test_banana_detection():
    """新增的香蕉检测测试方法"""
    # 配置
    image_path = 'data/test_images/fruit.jpg'
    output_dir = 'data/outputs'
    output_path = os.path.join(output_dir, 'fruit_detected.jpg')
    model_path = MODEL_PATH

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 读取图片
    image = cv2.imread(image_path)
    if image is None:
        print(f'无法读取图片: {image_path}')
        return

    # 初始化检测器
    detector = YoloDetector(model_path)

    # 检测，target_class传入'香蕉'
    valid_boxes, vis_img = detector.detect(image, target_class='banana')

    # 输出检测结果
    print('检测到的目标:', valid_boxes)

    # 保存可视化图片
    save_image(vis_img, output_path)
    print(f'检测结果已保存到: {output_path}')

if __name__ == '__main__':
    print("选择测试方法:")
    print("1. 批量测试 (检测多张图片)")
    print("2. 香蕉检测测试 (检测fruit.jpg中的香蕉)")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == '1':
        print("\n=== 批量测试 ===")
        test_batch_detection()
    elif choice == '2':
        print("\n=== 香蕉检测测试 ===")
        test_banana_detection()
    else:
        print("无效选择，默认运行批量测试")
        test_batch_detection() 