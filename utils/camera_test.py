import cv2
import time
import numpy as np
from typing import List, Tuple
import pyrealsense2 as rs
import os
from datetime import datetime


def test_cameras(max_cameras: int = 10, display_time: int = 30) -> List[Tuple[int, bool]]:
    """
    测试多个相机并返回结果
    
    Args:
        max_cameras: 最大测试相机数量
        display_time: 每个相机显示时间（秒）
    
    Returns:
        List of tuples: (camera_index, is_working)
    """
    results = []
    
    print(f"开始测试相机，最多测试 {max_cameras} 个相机...")
    print("按 'q' 键跳过当前相机，按 'ESC' 退出程序")
    print("-" * 50)
    
    for camera_index in range(max_cameras):
        print(f"\n正在测试相机 {camera_index}...")
        
        # 尝试打开相机
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"相机 {camera_index}: 无法打开")
            results.append((camera_index, False))
            continue
        
        # 设置相机属性
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # 读取一帧测试
        ret, frame = cap.read()
        if not ret:
            print(f"相机 {camera_index}: 无法读取图像")
            cap.release()
            results.append((camera_index, False))
            continue
        
        print(f"相机 {camera_index}: 成功打开，分辨率: {frame.shape[1]}x{frame.shape[0]}")
        
        # 显示图像流
        start_time = time.time()
        window_name = f"Camera {camera_index}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        try:
            while time.time() - start_time < display_time:
                ret, frame = cap.read()
                if not ret:
                    print(f"相机 {camera_index}: 读取图像失败")
                    break
                
                # 在图像上显示信息
                info_text = f"Camera {camera_index} - Press 'q' to skip, 'ESC' to exit, 'k' to capture"
                cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 255, 0), 2)
                
                # 显示剩余时间
                remaining_time = display_time - (time.time() - start_time)
                time_text = f"Time: {remaining_time:.1f}s"
                cv2.putText(frame, time_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 255, 0), 2)
                
                cv2.imshow(window_name, frame)
                
                # 检查按键
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print(f"用户跳过相机 {camera_index}")
                    break
                elif key == ord('k'):
                    # 拍照功能
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"camera_{camera_index}_{timestamp}.jpg"
                    save_path = os.path.join("data", "cam_capture", filename)
                    
                    # 确保目录存在
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    
                    if cv2.imwrite(save_path, frame):
                        print(f"照片已保存: {save_path}")
                        # 在图像上显示保存成功的信息
                        cv2.putText(frame, "Photo Saved!", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.7, (0, 255, 0), 2)
                    else:
                        print(f"保存照片失败: {save_path}")
                        cv2.putText(frame, "Save Failed!", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.7, (0, 0, 255), 2)
                elif key == 27:  # ESC
                    print("用户退出程序")
                    cap.release()
                    cv2.destroyAllWindows()
                    return results
                
        except Exception as e:
            print(f"相机 {camera_index}: 显示过程中出错 - {e}")
        
        # 释放资源
        cap.release()
        cv2.destroyWindow(window_name)
        
        results.append((camera_index, True))
        print(f"相机 {camera_index} 测试完成")
    
    print("\n" + "=" * 50)
    print("相机测试结果:")
    working_cameras = [idx for idx, working in results if working]
    if working_cameras:
        print(f"可用的相机编号: {working_cameras}")
    else:
        print("未找到可用的相机")
    
    return results


def test_camera_with_info(camera_index: int, display_time: int = 30) -> bool:
    """
    测试单个相机并显示详细信息
    
    Args:
        camera_index: 相机编号
        display_time: 显示时间（秒）
    
    Returns:
        bool: 相机是否可用
    """
    print(f"\n详细测试相机 {camera_index}...")
    
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"相机 {camera_index}: 无法打开")
        return False
    
    # 获取相机信息
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    
    print(f"相机 {camera_index} 信息:")
    print(f"  分辨率: {width}x{height}")
    print(f"  FPS: {fps}")
    print(f"  编码格式: {chr(fourcc & 0xFF)}{chr((fourcc >> 8) & 0xFF)}{chr((fourcc >> 16) & 0xFF)}{chr((fourcc >> 24) & 0xFF)}")
    
    # 显示图像流
    start_time = time.time()
    window_name = f"Camera {camera_index} - Detailed Test"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    try:
        while time.time() - start_time < display_time:
            ret, frame = cap.read()
            if not ret:
                print(f"相机 {camera_index}: 读取图像失败")
                break
            
            # 显示详细信息
            info_lines = [
                f"Camera {camera_index}",
                f"Resolution: {width}x{height}",
                f"FPS: {fps:.1f}",
                f"Press 'q' to skip, 'ESC' to exit, 'k' to capture"
            ]
            
            for i, line in enumerate(info_lines):
                cv2.putText(frame, line, (10, 30 + i * 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # 显示剩余时间
            remaining_time = display_time - (time.time() - start_time)
            time_text = f"Time: {remaining_time:.1f}s"
            cv2.putText(frame, time_text, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0, 255, 0), 2)
            
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print(f"用户跳过相机 {camera_index}")
                break
            elif key == ord('k'):
                # 拍照功能
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"camera_{camera_index}_{timestamp}.jpg"
                save_path = os.path.join("data", "cam_capture", filename)
                
                # 确保目录存在
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                if cv2.imwrite(save_path, frame):
                    print(f"照片已保存: {save_path}")
                    # 在图像上显示保存成功的信息
                    cv2.putText(frame, "Photo Saved!", (10, 175), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.7, (0, 255, 0), 2)
                else:
                    print(f"保存照片失败: {save_path}")
                    cv2.putText(frame, "Save Failed!", (10, 175), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.7, (0, 0, 255), 2)
            elif key == 27:  # ESC
                print("用户退出程序")
                cap.release()
                cv2.destroyAllWindows()
                return True
    
    except Exception as e:
        print(f"相机 {camera_index}: 显示过程中出错 - {e}")
    
    cap.release()
    cv2.destroyWindow(window_name)
    return True


def test_realsense_cameras():
    """
    遍历所有连接的RealSense深度相机，显示视频流和深度流
    """
    try:
        # 打印所有连接的RealSense设备
        context = rs.context()
        devices = list(context.query_devices())
        
        if not devices:
            print("未找到任何RealSense设备")
            return
        
        print(f"找到 {len(devices)} 个RealSense深度相机:")
        for device in devices:
            serial = device.get_info(rs.camera_info.serial_number)
            name = device.get_info(rs.camera_info.name)
            print(f"  设备名称: {name}")
            print(f"  序列号: {serial}")
        
        print("\n开始遍历深度相机...")
        print("按 'q' 键切换到下一个相机，按 'k' 键拍照，按 'ESC' 退出程序")
        print("-" * 50)
        
        # 遍历每个设备
        for device in devices:
            serial = device.get_info(rs.camera_info.serial_number)
            name = device.get_info(rs.camera_info.name)
            
            print(f"\n正在测试设备: {name}")
            print(f"序列号: {serial}")
            
            # 配置管道
            pipeline = rs.pipeline()
            config = rs.config()
            config.enable_device(serial)
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            
            try:
                # 启动管道
                profile = pipeline.start(config)                
                                
                # 创建窗口
                color_window = f"Color - {name}"
                depth_window = f"Depth - {name}"
                cv2.namedWindow(color_window, cv2.WINDOW_NORMAL)
                cv2.namedWindow(depth_window, cv2.WINDOW_NORMAL)
                
                print("显示视频流和深度流，按 'q' 切换到下一个相机...")
                
                while True:
                    # 等待帧
                    frames = pipeline.wait_for_frames()
                    color_frame = frames.get_color_frame()
                    depth_frame = frames.get_depth_frame()
                    
                    if not color_frame or not depth_frame:
                        continue
                    
                    # 转换为numpy数组
                    color_image = np.asanyarray(color_frame.get_data())
                    depth_image = np.asanyarray(depth_frame.get_data())
                    
                    # 深度图像转换为可显示的格式
                    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
                    
                    # 在图像上显示信息
                    info_text = f"Device: {name} - Press 'k' to capture"
                    cv2.putText(color_image, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(depth_colormap, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # 显示图像
                    cv2.imshow(color_window, color_image)
                    cv2.imshow(depth_window, depth_colormap)
                    
                    # 检查按键
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        print(f"切换到下一个相机...")
                        break
                    elif key == ord('k'):
                        # 拍照功能 - 保存彩色图像和深度图像
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        color_filename = f"realsense_color_{serial}_{timestamp}.jpg"
                        depth_filename = f"realsense_depth_{serial}_{timestamp}.png"
                        
                        color_save_path = os.path.join("data", "cam_capture", color_filename)
                        depth_save_path = os.path.join("data", "cam_capture", depth_filename)
                        
                        # 确保目录存在
                        os.makedirs(os.path.dirname(color_save_path), exist_ok=True)
                        
                        # 保存彩色图像
                        color_saved = cv2.imwrite(color_save_path, color_image)
                        # 保存深度图像（原始深度数据）
                        depth_saved = cv2.imwrite(depth_save_path, depth_image)
                        
                        if color_saved and depth_saved:
                            print(f"照片已保存: {color_save_path}")
                            print(f"深度图已保存: {depth_save_path}")
                            # 在图像上显示保存成功的信息
                            cv2.putText(color_image, "Photos Saved!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                                       0.7, (0, 255, 0), 2)
                            cv2.putText(depth_colormap, "Photos Saved!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                                       0.7, (0, 255, 0), 2)
                        else:
                            print(f"保存照片失败")
                            cv2.putText(color_image, "Save Failed!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                                       0.7, (0, 0, 255), 2)
                            cv2.putText(depth_colormap, "Save Failed!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                                       0.7, (0, 0, 255), 2)
                    elif key == 27:  # ESC
                        print("用户退出程序")
                        pipeline.stop()
                        cv2.destroyAllWindows()
                        return
                
            except Exception as e:
                print(f"设备 {name} 测试失败: {e}")
            finally:
                # 释放资源
                pipeline.stop()
                cv2.destroyWindow(color_window)
                cv2.destroyWindow(depth_window)
                print(f"设备 {name} 测试完成")
        
        print("\n所有RealSense设备测试完成！")
        
    except Exception as e:
        print(f"RealSense设备测试失败: {e}")


if __name__ == "__main__":
    print("相机测试程序")
    print("=" * 50)
    
    # 选择测试类型
    print("选择测试类型:")
    print("1. 普通相机测试")
    print("2. RealSense深度相机测试")
    
    try:
        choice = input("请输入选择 (1 或 2): ").strip()
        
        if choice == "1":
            # 快速测试所有相机
            results = test_cameras(max_cameras=20, display_time=100)
            
            # 询问是否要详细测试某个相机
            working_cameras = [idx for idx, working in results if working]
            if working_cameras:
                print(f"\n找到 {len(working_cameras)} 个可用相机: {working_cameras}")
                
                while True:
                    try:
                        choice = input("\n输入相机编号进行详细测试 (或按回车退出): ").strip()
                        if not choice:
                            break
                        
                        camera_idx = int(choice)
                        if camera_idx in working_cameras:
                            test_camera_with_info(camera_idx, display_time=30)
                        else:
                            print(f"相机 {camera_idx} 不可用或未测试")
                    except ValueError:
                        print("请输入有效的数字")
                    except KeyboardInterrupt:
                        break
        
        elif choice == "2":
            test_realsense_cameras()
        
        else:
            print("无效选择")
    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    
    print("\n测试完成！") 