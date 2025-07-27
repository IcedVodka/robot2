import cv2
import numpy as np
import pyrealsense2 as rs
from image_segmentation import ImageSegmentation
import time
from utils.vertical_grab.interface import vertical_catch


class RealtimeSegmentation:
    """实时分割类，集成深度相机和图像分割功能"""
    
    def __init__(self, yolo_model_path: str = "/home/gml-cwl/code/my_robot/yolov8s-world.pt", 
                 sam_model_path: str = "/home/gml-cwl/code/my_robot/sam_b.pt"):
        """
        初始化实时分割器
        
        Args:
            yolo_model_path: YOLO模型路径
            sam_model_path: SAM模型路径
        """
        self.segmenter = ImageSegmentation(yolo_model_path, sam_model_path)
        self.pipeline = None
        self.config = None
        self.align = None
        self.current_frame = None
        self.current_depth = None
        self.is_captured = False
        
        # 添加抓取相关参数
        self.color_intr = {"ppx": 331.054, "ppy": 240.211, "fx": 604.248, "fy": 604.376}  # RGB相机内参
        self.arm_gripper_length = 0.8  # 机械臂抓手长度
        self.vertical_rx_ry_rz = [3.14, 0, 0]  # 垂直抓取时的旋转角度
        self.rotation_matrix = [[0.00881983, -0.99903671, -0.04298679],
                               [0.99993794,  0.00910406, -0.00642086],
                               [0.00680603, -0.04292749, 0.99905501]]  # 旋转矩阵
        self.translation_vector = [0.09830079, -0.04021631, -0.01756948]  # 平移向量
        
    def init_camera(self):
        """初始化深度相机"""
        try:
            # 创建RealSense管道
            self.pipeline = rs.pipeline()
            self.config = rs.config()
            
            # 配置深度和彩色流
            self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            
            # 启动管道
            profile = self.pipeline.start(self.config)
            
            # 创建对齐对象
            depth_sensor = profile.get_device().first_depth_sensor()
            depth_scale = depth_sensor.get_depth_scale()
            print(f"Depth Scale is: {depth_scale}")
            
            # 创建对齐处理器
            align_to = rs.stream.color
            self.align = rs.align(align_to)
            
            print("深度相机初始化成功")
            return True
            
        except Exception as e:
            print(f"相机初始化失败: {e}")
            return False
    
    def capture_frame(self):
        """捕获一帧图像"""
        try:
            # 等待一帧数据
            frames = self.pipeline.wait_for_frames()
            
            # 对齐深度帧到彩色帧
            aligned_frames = self.align.process(frames)
            
            # 获取对齐后的帧
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                return False
            
            # 转换为numpy数组
            self.current_frame = np.asanyarray(color_frame.get_data())
            self.current_depth = np.asanyarray(depth_frame.get_data())
            
            return True
            
        except Exception as e:
            print(f"帧捕获失败: {e}")
            return False
    
    def get_depth_at_point(self, x: int, y: int) -> float:
        """获取指定点的深度值（米）"""
        if self.current_depth is None:
            return 0.0
        
        # 获取深度值（毫米）
        depth_mm = self.current_depth[y, x]
        # 转换为米
        depth_m = depth_mm / 1000.0
        return depth_m
    
    def calculate_grasp_poses(self, mask: np.ndarray, selected_point: tuple, depth: float) -> tuple:
        """
        计算抓取位姿
        
        Args:
            mask: 分割掩码
            selected_point: 选择的点坐标 (x, y)
            depth: 深度值（米）
            
        Returns:
            tuple: (above_object_pose, correct_angle_pose, finally_pose)
        """
        try:
            # 模拟当前机械臂位姿（实际应用中应该从机械臂获取）
            current_pose = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # [x, y, z, rx, ry, rz]
            
            # 将深度值转换为毫米
            depth_mm = depth * 1000.0
            
            # 计算抓取位姿
            above_object_pose, correct_angle_pose, finally_pose = vertical_catch(
                mask=mask,
                depth_frame=self.current_depth,
                color_intr=self.color_intr,
                current_pose=current_pose,
                arm_gripper_length=self.arm_gripper_length,
                vertical_rx_ry_rz=self.vertical_rx_ry_rz,
                rotation_matrix=self.rotation_matrix,
                translation_vector=self.translation_vector,
                use_point_depth_or_mean=True
            )
            
            return above_object_pose, correct_angle_pose, finally_pose
            
        except Exception as e:
            print(f"计算抓取位姿时出错: {e}")
            return None, None, None
    
    def print_grasp_poses(self, above_pose, correct_pose, finally_pose):
        """打印抓取位姿信息"""
        print("\n" + "="*50)
        print("机械臂抓取位姿计算结果")
        print("="*50)
        
        if above_pose is not None:
            print("位点1 - 物体上方位姿:")
            print(f"  X: {above_pose[0]:.3f} m")
            print(f"  Y: {above_pose[1]:.3f} m") 
            print(f"  Z: {above_pose[2]:.3f} m")
            print(f"  RX: {above_pose[3]:.3f} rad")
            print(f"  RY: {above_pose[4]:.3f} rad")
            print(f"  RZ: {above_pose[5]:.3f} rad")
            print()
        
        if correct_pose is not None:
            print("位点2 - 角度调整位姿:")
            print(f"  X: {correct_pose[0]:.3f} m")
            print(f"  Y: {correct_pose[1]:.3f} m")
            print(f"  Z: {correct_pose[2]:.3f} m")
            print(f"  RX: {correct_pose[3]:.3f} rad")
            print(f"  RY: {correct_pose[4]:.3f} rad")
            print(f"  RZ: {correct_pose[5]:.3f} rad")
            print()
        
        if finally_pose is not None:
            print("位点3 - 最终抓取位姿:")
            print(f"  X: {finally_pose[0]:.3f} m")
            print(f"  Y: {finally_pose[1]:.3f} m")
            print(f"  Z: {finally_pose[2]:.3f} m")
            print(f"  RX: {finally_pose[3]:.3f} rad")
            print(f"  RY: {finally_pose[4]:.3f} rad")
            print(f"  RZ: {finally_pose[5]:.3f} rad")
            print()
        
        print("抓取流程说明:")
        print("1. 移动到物体上方位姿 (位点1)")
        print("2. 调整角度到正确抓取角度 (位点2)")
        print("3. 下降到最终抓取位姿 (位点3)")
        print("4. 闭合夹爪进行抓取")
        print("5. 抬起物体")
        print("="*50)
    
    def manual_selection_with_depth(self, image: np.ndarray) -> tuple:
        """手动选择目标并获取深度信息"""
        print("点击选择目标对象，按Enter确认，按ESC取消")
        
        selected_point = None
        depth_value = 0.0
        
        def mouse_callback(event, x, y, flags, param):
            nonlocal selected_point, depth_value
            if event == cv2.EVENT_LBUTTONDOWN:
                selected_point = (x, y)
                depth_value = self.get_depth_at_point(x, y)
                print(f"选择点: ({x}, {y}), 深度: {depth_value:.3f}米")
                print("按Enter键确认选择，或继续点击选择其他点")
        
        # 创建窗口并设置鼠标回调
        cv2.namedWindow('Select Target Object')
        cv2.setMouseCallback('Select Target Object', mouse_callback)
        
        while True:
            # 显示图像
            display_img = image.copy()
            
            # 如果已选择点，绘制标记
            if selected_point:
                cv2.circle(display_img, selected_point, 10, (0, 255, 0), 2)
                cv2.putText(display_img, f"Depth: {depth_value:.3f}m", 
                           (selected_point[0] + 15, selected_point[1] - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                # 添加确认提示
                cv2.putText(display_img, "Press ENTER to confirm", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(display_img, "Press ESC to cancel", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            else:
                # 添加选择提示
                cv2.putText(display_img, "Click to select target", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(display_img, "Press ESC to cancel", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            cv2.imshow('Select Target Object', display_img)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC键
                selected_point = None
                break
            elif key == 13 and selected_point:  # Enter键确认选择
                print("确认选择，开始分割...")
                break
        
        cv2.destroyAllWindows()
        return selected_point, depth_value
    
    def run_realtime_segmentation(self):
        """运行实时分割程序"""
        if not self.init_camera():
            print("相机初始化失败，程序退出")
            return
        
        print("实时分割程序启动")
        print("按 'q' 拍照并进行分割")
        print("按 'ESC' 退出程序")
        
        try:
            while True:
                # 捕获帧
                if not self.capture_frame():
                    continue
                
                # 显示实时图像
                cv2.imshow('Real-time Camera', self.current_frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == 27:  # ESC键退出
                    break
                elif key == ord('q'):  # q键拍照
                    print("拍照并开始分割...")
                    self.process_captured_image()
                
        except KeyboardInterrupt:
            print("程序被用户中断")
        finally:
            self.cleanup()
    
    def process_captured_image(self):
        """处理捕获的图像"""
        if self.current_frame is None:
            print("没有可用的图像")
            return
        
        # 保存当前帧
        timestamp = int(time.time())
        image_filename = f"captured_image_{timestamp}.jpg"
        cv2.imwrite(image_filename, self.current_frame)
        print(f"图像已保存: {image_filename}")
        
        # 手动选择目标
        selected_point, depth = self.manual_selection_with_depth(self.current_frame)
        
        if selected_point is None:
            print("未选择目标，取消分割")
            return
        
        print(f"选择的目标点: {selected_point}, 深度: {depth:.3f}米")
        
        # 执行分割
        try:
            print("正在使用SAM模型进行分割...")
            # 使用手动选择模式进行分割
            mask = self.segmenter.segment(
                image_input=self.current_frame,
                auto_select=False,  # 使用手动选择
                output_mask=f"segmentation_mask_{timestamp}.png",
                save_visualization=True,
                manual_point=selected_point  # 传递选择点
            )
            
            if mask is not None:
                print("分割成功！")
                print(f"掩码已保存: segmentation_mask_{timestamp}.png")
                
                # 计算抓取位姿
                print("正在计算抓取位姿...")
                above_pose, correct_pose, finally_pose = self.calculate_grasp_poses(
                    mask, selected_point, depth
                )
                
                # 打印抓取位姿
                self.print_grasp_poses(above_pose, correct_pose, finally_pose)
                
                # 显示分割结果
                self.display_segmentation_result(mask, selected_point, depth)
            else:
                print("分割失败")
                
        except Exception as e:
            print(f"分割过程中出现错误: {e}")
    
    def display_segmentation_result(self, mask: np.ndarray, selected_point: tuple, depth: float):
        """显示分割结果"""
        # 创建结果图像
        result_img = self.current_frame.copy()
        
        # 将掩码转换为彩色图像
        mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        mask_colored[mask > 0] = [0, 255, 0]  # 绿色显示分割区域
        
        # 叠加显示
        alpha = 0.3
        result_img = cv2.addWeighted(result_img, 1-alpha, mask_colored, alpha, 0)
        
        # 标记选择点
        cv2.circle(result_img, selected_point, 10, (0, 0, 255), 2)
        cv2.putText(result_img, f"Depth: {depth:.3f}m", 
                   (selected_point[0] + 15, selected_point[1] - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # 显示结果
        cv2.imshow('Segmentation Result', result_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    def cleanup(self):
        """清理资源"""
        if self.pipeline:
            self.pipeline.stop()
        cv2.destroyAllWindows()
        print("程序已退出")


def main():
    """主函数"""
    # 创建实时分割器
    realtime_seg = RealtimeSegmentation()
    
    # 运行实时分割程序
    realtime_seg.run_realtime_segmentation()


if __name__ == '__main__':
    main() 