import cv2
import numpy as np
import os
import sys
import time

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Robot.sensor.depth_camera import RealsenseSensor, print_realsense_devices
from policy.segmentation import SamPredictor

class DepthCameraSamTest:
    """
    深度相机 + SAM分割测试程序
    
    功能：
    1. 显示深度相机彩色图像
    2. 支持鼠标点击选择点进行SAM分割
    3. 按'q'暂停视频流，按'e'继续视频流
    4. 按'ESC'退出程序
    5. 显示分割结果和深度信息
    """
    
    def __init__(self):
        self.sensor = None
        self.sam_predictor = None
        self.paused = False
        self.clicked_points = []
        self.current_mask = None
        self.window_name = "Depth Camera + SAM"
        self.running = True
        
        # SAM模型路径
        self.sam_model_path = "/home/gml-cwl/code/robot2/assets/weights/sam_l.pt"
        
    def mouse_callback(self, event, x, y, flags, param):
        """鼠标回调函数，记录点击的点并进行分割"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.clicked_points.append((x, y))
            print(f"点击位置: ({x}, {y})")
            
            # 进行SAM分割
            self.perform_sam_segmentation(x, y)
    
    def setup_camera(self, camera_serial=None):
        """设置深度相机"""
        print("正在初始化深度相机...")
        
        # 如果没有指定序列号，先打印可用设备
        if camera_serial is None:
            print_realsense_devices()
            camera_serial = input("请输入相机序列号（直接回车使用第一个可用设备）: ").strip()
            if not camera_serial:
                # 获取第一个可用设备
                try:
                    import pyrealsense2 as rs
                    context = rs.context()
                    devices = list(context.query_devices())
                    if devices:
                        camera_serial = devices[0].get_info(rs.camera_info.serial_number)
                        print(f"使用第一个可用设备，序列号: {camera_serial}")
                    else:
                        print("未找到可用设备")
                        return False
                except Exception as e:
                    print(f"获取设备列表失败: {e}")
                    return False
        
        try:
            # 初始化传感器
            self.sensor = RealsenseSensor("depth_sam_test")
            
            # 设置相机参数（启用深度流）
            self.sensor.set_up(
                camera_serial=camera_serial,
                is_depth=True,
                resolution=[1280, 720]
            )
            
            print("深度相机初始化成功！")
            return True
            
        except Exception as e:
            print(f"相机初始化失败: {e}")
            return False
    
    def setup_sam(self):
        """设置SAM分割模型"""
        print("正在初始化SAM模型...")
        try:
            self.sam_predictor = SamPredictor(self.sam_model_path)
            print("SAM模型初始化成功！")
            return True
        except Exception as e:
            print(f"SAM模型初始化失败: {e}")
            return False
    
    def perform_sam_segmentation(self, x, y):
        """执行SAM分割"""
        if self.sam_predictor is None:
            print("SAM模型未初始化")
            return
        
        try:
            # 获取当前图像
            data = self.sensor.get_information()
            if data and "color" in data:
                color_image = data["color"]
                
                # 转换为RGB格式（SAM需要RGB格式）
                rgb_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
                
                # 执行SAM分割
                center, mask = self.sam_predictor.predict(rgb_image, points=[x, y])
                
                if mask is not None:
                    self.current_mask = mask
                    print(f"分割成功！点击点 ({x}, {y}) 的分割结果已生成")
                    
                    # 显示深度信息
                    if data and "depth" in data:
                        depth_image = data["depth"]
                        if 0 <= y < depth_image.shape[0] and 0 <= x < depth_image.shape[1]:
                            depth_value = depth_image[y, x]
                            print(f"点击点深度值: {depth_value} mm")
                else:
                    print("分割失败，未生成有效掩码")
                    
        except Exception as e:
            print(f"SAM分割失败: {e}")
    
    def draw_segmentation_result(self, image):
        """在图像上绘制分割结果和选择的点"""
        if image is None:
            return image
            
        img_copy = image.copy()
        
        # 绘制选择的点
        for i, (x, y) in enumerate(self.clicked_points):
            # 绘制圆圈
            cv2.circle(img_copy, (x, y), 5, (0, 255, 0), -1)
            # 绘制序号
            cv2.putText(img_copy, str(i+1), (x+10, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # 绘制分割掩码
        if self.current_mask is not None:
            # 创建彩色掩码
            mask_colored = np.zeros_like(img_copy)
            mask_colored[self.current_mask > 0] = [0, 0, 255]  # 红色显示分割区域
            
            # 将掩码叠加到原图上
            alpha = 0.3
            img_copy = cv2.addWeighted(img_copy, 1-alpha, mask_colored, alpha, 0)
            
            # 绘制分割边界
            contours, _ = cv2.findContours(self.current_mask.astype(np.uint8), 
                                         cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(img_copy, contours, -1, (255, 0, 0), 2)
        
        return img_copy
    
    def run_stream(self):
        """运行视频流"""
        print("\n=== 深度相机 + SAM分割测试 ===")
        print("操作说明:")
        print("- 鼠标点击: 在图像上选择点进行SAM分割")
        print("- 按 'q': 暂停视频流")
        print("- 按 'e': 继续视频流")
        print("- 按 'c': 清除所有选择的点和分割结果")
        print("- 按 'ESC': 退出程序")
        print("=" * 40)
        
        # 创建窗口并设置鼠标回调
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        try:
            while self.running:
                if not self.paused:
                    # 获取传感器数据
                    data = self.sensor.get_information()
                    
                    if data and "color" in data:
                        color_image = data["color"]
                        
                        # 绘制分割结果和选择的点
                        result_image = self.draw_segmentation_result(color_image)
                        
                        # 显示图像
                        cv2.imshow(self.window_name, result_image)
                        
                        # 显示状态信息
                        status_text = "PAUSED" if self.paused else "RUNNING"
                        mask_status = "有分割" if self.current_mask is not None else "无分割"
                        print(f"\r状态: {status_text} | 选择点数: {len(self.clicked_points)} | 分割状态: {mask_status}", 
                              end="", flush=True)
                
                # 处理键盘输入
                key = cv2.waitKey(1) & 0xFF
                
                if key == 27:  # ESC键
                    print("\n退出程序...")
                    break
                elif key == ord('q'):  # q键 - 暂停
                    self.paused = True
                    print("\n视频流已暂停")
                elif key == ord('e'):  # e键 - 继续
                    self.paused = False
                    print("\n视频流已继续")
                elif key == ord('c'):  # c键 - 清除
                    self.clicked_points.clear()
                    self.current_mask = None
                    print("\n已清除所有选择的点和分割结果")
                elif key == ord('s'):  # s键 - 保存分割结果
                    if self.current_mask is not None:
                        output_path = "/home/gml-cwl/code/robot2/data/outputs/sam_segmentation.png"
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        cv2.imwrite(output_path, self.current_mask * 255)
                        print(f"\n分割结果已保存到: {output_path}")
                
        except KeyboardInterrupt:
            print("\n程序被用户中断")
        except Exception as e:
            print(f"\n程序运行出错: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        print("\n正在清理资源...")
        cv2.destroyAllWindows()
        if self.sensor:
            self.sensor.cleanup()
        print("资源清理完成")

def main():
    """主函数"""
    print("深度相机 + SAM分割测试程序")
    print("=" * 50)
    
    # 创建测试实例
    test = DepthCameraSamTest()
    
    # 设置相机
    if not test.setup_camera():
        print("相机设置失败，程序退出")
        return
    
    # 设置SAM模型
    if not test.setup_sam():
        print("SAM模型设置失败，程序退出")
        return
    
    # 运行视频流
    test.run_stream()

if __name__ == "__main__":
    main() 