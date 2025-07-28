#!/usr/bin/env python3
"""
RGB摄像头传感器测试程序

这个程序演示了如何使用RgbCameraSensor类的基本功能：
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

from Robot.sensor.rgb_camera import RgbCameraSensor

def test_rgb_camera_sensor():
    """测试RGB摄像头传感器功能"""
    print("=== RGB摄像头传感器测试程序 ===")
    
    # 摄像头ID - 请根据实际情况修改
    camera_id = 14  # 通常0是默认摄像头
    
    sensor = None
    try:
        # 1. 初始化传感器
        print("1. 初始化RGB摄像头传感器...")
        sensor = RgbCameraSensor(name="test_camera")
        
        # 2. 设置相机参数
        print("2. 设置相机参数...")
        sensor.set_up(camera_id=camera_id)
        
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
                cv2.putText(color_frame, f"Camera ID: {camera_id}", (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("RGB Camera", color_frame)
                
                # 处理按键
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("用户退出程序")
                    break
                elif key == ord('s'):
                    # 保存当前帧
                    timestamp = int(time.time())
                    filename = f"rgb_camera_{timestamp}.jpg"
                    cv2.imwrite(filename, color_frame)
                    print(f"已保存图像: {filename}")
            else:
                print("未获取到图像数据")
                time.sleep(0.1)
                
    except RuntimeError as e:
        print(f"错误: {e}")
        print("请检查:")
        print("1. 摄像头是否正确连接")
        print("2. 摄像头ID是否正确")
        print("3. 摄像头是否被其他程序占用")
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

def test_multiple_cameras():
    """测试多个摄像头"""
    print("\n=== 多摄像头测试 ===")
    
    # 测试多个摄像头ID
    camera_ids = [0, 1, 2]
    
    for camera_id in camera_ids:
        print(f"\n测试摄像头 ID: {camera_id}")
        sensor = None
        try:
            sensor = RgbCameraSensor(name=f"test_camera_{camera_id}")
            sensor.set_up(camera_id=camera_id)
            
            # 尝试获取几帧图像
            for i in range(10):
                data = sensor.get_information()
                if data and "color" in data:
                    print(f"摄像头 {camera_id} 工作正常")
                    break
                time.sleep(0.1)
            else:
                print(f"摄像头 {camera_id} 无法获取图像")
                
        except Exception as e:
            print(f"摄像头 {camera_id} 初始化失败: {e}")
        finally:
            if sensor:
                sensor.cleanup()

if __name__ == "__main__":
    # 运行基本测试
    test_rgb_camera_sensor()
    
    # 可选：运行多摄像头测试
    # test_multiple_cameras() 