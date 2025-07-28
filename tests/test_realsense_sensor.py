#!/usr/bin/env python3
"""
RealSense传感器测试程序

这个程序演示了如何使用RealsenseSensor类的基本功能：
1. 初始化传感器
2. 设置相机参数
3. 获取图像数据
4. 显示图像
5. 清理资源
"""

import sys
import os
import cv2
import numpy as np
import time


# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Robot.sensor.depth_camera import RealsenseSensor, print_realsense_devices

def test_realsense_sensor():
    """测试RealSense传感器功能"""
    print("=== RealSense传感器测试程序 ===")
    
    # 相机序列号 - 请根据实际情况修改
    camera_serial = "327122072195"  # 请替换为实际的相机序列号
    camera_serial2 = "207522073950"
    
    sensor = None
    try:
        # 1. 初始化传感器
        print("1. 初始化RealSense传感器...")
        sensor = RealsenseSensor("test_realsense")
        
        # 2. 设置相机参数
        print("2. 设置相机参数...")
        sensor.set_up(camera_serial=camera_serial2, is_depth=True)
        
        # 3. 获取并显示图像
        print("3. 开始获取图像数据...")
        print("按 'q' 键退出，按 's' 键保存当前帧")
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            # 获取最新数据
            data = sensor.get_information()
            
            if data and "color" in data:
                frame_count += 1
                current_time = time.time()
                fps = frame_count / (current_time - start_time)
                
                # 显示彩色图像
                color_frame = data["color"]
                cv2.putText(color_frame, f"FPS: {fps:.1f}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("RealSense Color", color_frame)
                
                # 如果有深度数据，显示深度图像
                if "depth" in data and data["depth"] is not None:
                    depth_frame = data["depth"]
                    # 将深度图像转换为可显示的格式
                    depth_colormap = cv2.applyColorMap(
                        cv2.convertScaleAbs(depth_frame, alpha=0.03), 
                        cv2.COLORMAP_JET
                    )
                    cv2.imshow("RealSense Depth", depth_colormap)
                
                # 处理按键
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("用户退出程序")
                    break
                elif key == ord('s'):
                    # 保存当前帧
                    timestamp = int(time.time())
                    cv2.imwrite(f"realsense_color_{timestamp}.jpg", color_frame)
                    if "depth" in data and data["depth"] is not None:
                        cv2.imwrite(f"realsense_depth_{timestamp}.png", data["depth"])
                    print(f"已保存图像: realsense_color_{timestamp}.jpg")
            else:
                print("未获取到图像数据")
                time.sleep(0.1)
                
    except RuntimeError as e:
        print(f"错误: {e}")
        print("请检查:")
        print("1. RealSense相机是否正确连接")
        print("2. 相机序列号是否正确")
        print("3. 是否安装了pyrealsense2库")
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"未知错误: {e}")
    finally:
        # 清理资源
        if sensor:
            print("4. 清理传感器资源...")
            sensor.cleanup()
        
        cv2.destroyAllWindows()
        print("测试程序结束")

if __name__ == "__main__":
    print_realsense_devices()
    test_realsense_sensor() 
