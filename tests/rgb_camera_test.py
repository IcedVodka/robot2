#!/usr/bin/env python3
"""
RGB相机测试脚本
演示如何使用RGBCamera类
"""

import sys
import os
import yaml
import cv2
import numpy as np

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Robot.sensor.rgb_camera import RGBCamera, create_rgb_camera_from_config


def load_config():
    """加载配置文件"""
    config_path = "configs/sensor_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def test_rgb_camera():
    """测试RGB相机功能"""
    print("=== RGB相机测试 ===")
    
    # 加载配置
    config = load_config()
    rgb_config = config['sensors']['rgb']
    
    print(f"相机配置: {rgb_config}")
    
    # 创建相机实例
    camera = create_rgb_camera_from_config(rgb_config)
    
    try:
        # 启动相机
        if not camera.start():
            print("相机启动失败")
            return
        
        print("相机启动成功")
        print(f"相机状态: {camera.get_status()}")
        
        # 测试数据读取
        print("\n开始读取图像数据...")
        frame_count = 0
        max_frames = 10000  # 测试100帧
        
        while frame_count < max_frames:
            # 获取最新帧（非阻塞）
            frame = camera.get_latest_frame()
            if frame is not None:
                frame_count += 1
                
                # 显示图像
                cv2.imshow('RGB Camera Test', frame)
                
                # 获取相机信息
                if frame_count % 30 == 0:  # 每30帧打印一次信息
                    info = camera.get_camera_info()
                    print(f"帧 {frame_count}: 分辨率={info['width']}x{info['height']}, "
                          f"实际FPS={info['fps_actual']:.1f}, 缓冲区大小={info['buffer_size']}")
                
                # 按'q'退出
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                # 没有数据时短暂等待
                import time
                time.sleep(0.01)
        
        print(f"\n测试完成，共读取 {frame_count} 帧")
        
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
    finally:
        # 停止相机
        camera.stop()
        cv2.destroyAllWindows()
        print("相机已停止")


def test_direct_creation():
    """测试直接创建相机实例"""
    print("\n=== 直接创建相机测试 ===")
    
    # 直接创建相机实例
    camera = RGBCamera(
        camera_id=0,
        width=640,
        height=480,
        fps=30,
        buffer_size=5
    )
    
    try:
        if camera.start():
            print("直接创建的相机启动成功")
            
            # 测试数据读取
            for i in range(10):
                frame = camera.get_latest_frame()
                if frame is not None:
                    print(f"获取到第 {i+1} 帧，形状: {frame.shape}")
                else:
                    print(f"第 {i+1} 次尝试未获取到数据")
                
                import time
                time.sleep(0.1)
        
        camera.stop()
        print("直接创建的相机测试完成")
        
    except Exception as e:
        print(f"直接创建测试错误: {e}")


if __name__ == "__main__":
    # 测试从配置文件创建
    test_rgb_camera()
    
    # 测试直接创建
    test_direct_creation()
    
    print("\n所有测试完成") 