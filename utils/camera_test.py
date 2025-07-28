import cv2
import time
import numpy as np
from typing import List, Tuple


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
                info_text = f"Camera {camera_index} - Press 'q' to skip, 'ESC' to exit"
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
                f"Press 'q' to skip, 'ESC' to exit"
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


if __name__ == "__main__":
    print("相机测试程序")
    print("=" * 50)
    
    # 快速测试所有相机
    results = test_cameras(max_cameras=20, display_time=30)
    
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
    
    print("\n测试完成！") 