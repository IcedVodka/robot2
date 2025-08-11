import numpy as np
import cv2
from typing import Tuple, Optional


def print_grasp_poses(above_pose, correct_pose, finally_pose , logger = None):
        """打印抓取位姿信息"""
        if logger:
            logger.debug("\n" + "="*50)
            logger.debug("机械臂抓取位姿计算结果")
            logger.debug("="*50)
        else:
            print("\n" + "="*50)
            print("机械臂抓取位姿计算结果")
            print("="*50)
        
        if above_pose is not None:
            if logger:
                logger.debug("位点1 - 物体上方位姿:")
                logger.debug(f"  X: {above_pose[0]:.3f} m")
                logger.debug(f"  Y: {above_pose[1]:.3f} m") 
                logger.debug(f"  Z: {above_pose[2]:.3f} m")
                logger.debug(f"  RX: {above_pose[3]:.3f} rad")
                logger.debug(f"  RY: {above_pose[4]:.3f} rad")
                logger.debug(f"  RZ: {above_pose[5]:.3f} rad")
                logger.debug("")
            else:
                print("位点1 - 物体上方位姿:")
                print(f"  X: {above_pose[0]:.3f} m")
                print(f"  Y: {above_pose[1]:.3f} m") 
                print(f"  Z: {above_pose[2]:.3f} m")
                print(f"  RX: {above_pose[3]:.3f} rad")
                print(f"  RY: {above_pose[4]:.3f} rad")
                print(f"  RZ: {above_pose[5]:.3f} rad")
                print()
        
        if correct_pose is not None:
            if logger:
                logger.debug("位点2 - 角度调整位姿:")
                logger.debug(f"  X: {correct_pose[0]:.3f} m")
                logger.debug(f"  Y: {correct_pose[1]:.3f} m")
                logger.debug(f"  Z: {correct_pose[2]:.3f} m")
                logger.debug(f"  RX: {correct_pose[3]:.3f} rad")
                logger.debug(f"  RY: {correct_pose[4]:.3f} rad")
                logger.debug(f"  RZ: {correct_pose[5]:.3f} rad")
                logger.debug("")
            else:
                print("位点2 - 角度调整位姿:")
                print(f"  X: {correct_pose[0]:.3f} m")
                print(f"  Y: {correct_pose[1]:.3f} m")
                print(f"  Z: {correct_pose[2]:.3f} m")
                print(f"  RX: {correct_pose[3]:.3f} rad")
                print(f"  RY: {correct_pose[4]:.3f} rad")
                print(f"  RZ: {correct_pose[5]:.3f} rad")
                print()
        
        if finally_pose is not None:
            if logger:
                logger.debug("位点3 - 最终抓取位姿:")
                logger.debug(f"  X: {finally_pose[0]:.3f} m")
                logger.debug(f"  Y: {finally_pose[1]:.3f} m")
                logger.debug(f"  Z: {finally_pose[2]:.3f} m")
                logger.debug(f"  RX: {finally_pose[3]:.3f} rad")
                logger.debug(f"  RY: {finally_pose[4]:.3f} rad")
                logger.debug(f"  RZ: {finally_pose[5]:.3f} rad")
                logger.debug("")
            else:
                print("位点3 - 最终抓取位姿:")
                print(f"  X: {finally_pose[0]:.3f} m")
                print(f"  Y: {finally_pose[1]:.3f} m")
                print(f"  Z: {finally_pose[2]:.3f} m")
                print(f"  RX: {finally_pose[3]:.3f} rad")
                print(f"  RY: {finally_pose[4]:.3f} rad")
                print(f"  RZ: {finally_pose[5]:.3f} rad")
                print()


def get_images(sensor, logger) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """获取彩色和深度图像"""
        try:
            data = sensor.get_information()
            if data and "color" in data and "depth" in data:
                last_color_image = data["color"].copy()
                last_depth_image = data["depth"].copy()
                return last_color_image, last_depth_image
            return None, None
        except Exception as e:
            logger.error(f"获取图像失败: {str(e)}")
            return None, None

def mark_detected_medicine_on_image(image: np.ndarray, bbox: list, depth: float,
                                   medicine_name: str, output_path: str) -> None:
    """
    在图片上标记识别到的药品边界框并保存
    
    Args:
        image: 原始图片 (BGR格式)
        bbox: 识别到的边界框坐标 [x1, y1, x2, y2]
        depth: 中心点的深度值
        medicine_name: 药品名称
        output_path: 输出图片路径
    """
    # 复制图片避免修改原图
    marked_image = image.copy()
    
    # 解析边界框坐标
    x1, y1, x2, y2 = bbox
    
    # 计算中心点坐标
    x = (x1 + x2) // 2
    y = (y1 + y2) // 2
    
    # 绘制边界框
    cv2.rectangle(marked_image, (x1, y1), (x2, y2), (0, 255, 0), 2)  # 绿色边界框
    
    # 绘制中心点
    cv2.circle(marked_image, (x, y), 5, (0, 0, 255), -1)  # 红色实心圆
    
    # 准备文本信息
    text_info = f"Medicine: {medicine_name}"
    coord_info = f"Box: ({x1}, {y1}, {x2}, {y2})"
    depth_info = f"Depth: {depth:.3f}mm"
    
    # 设置文本参数
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    color = (0, 255, 0)  # 绿色
    
    # 计算文本位置
    text_y_start = 30
    line_height = 25
    
    # 绘制文本
    cv2.putText(marked_image, text_info, (10, text_y_start), font, font_scale, color, thickness)
    cv2.putText(marked_image, coord_info, (10, text_y_start + line_height), font, font_scale, color, thickness)
    cv2.putText(marked_image, depth_info, (10, text_y_start + 2*line_height), font, font_scale, color, thickness)
    
    # 保存图片
    cv2.imwrite(output_path, marked_image)