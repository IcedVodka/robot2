import cv2
import numpy as np
from numpy import ndarray
from typing import Tuple
import copy
import numpy as np
from scipy.spatial.transform import Rotation as R


def convert(x, y, z, x1, y1, z1, rx, ry, rz, rotation_matrix, translation_vector):
    """
    接收单位 m

    我们需要将旋转向量和平移向量转换为齐次变换矩阵，然后使用深度相机识别到的物体坐标（x, y, z）和
    机械臂末端的位姿（x1,y1,z1,rx,ry,rz）来计算物体相对于机械臂基座的位姿（x, y, z, rx, ry, rz）

    """

    rotation_matrix = rotation_matrix
    translation_vector = translation_vector
    # 深度相机识别物体返回的坐标
    obj_camera_coordinates = np.array([x, y, z])

    # 机械臂末端的位姿，单位为弧度
    end_effector_pose = np.array([x1, y1, z1, rx, ry, rz])

    # 将旋转矩阵和平移向量转换为齐次变换矩阵
    T_camera_to_end_effector = np.eye(4)
    T_camera_to_end_effector[:3, :3] = rotation_matrix
    T_camera_to_end_effector[:3, 3] = translation_vector

    # 机械臂末端的位姿转换为齐次变换矩阵
    position = end_effector_pose[:3]
    orientation = R.from_euler("xyz", end_effector_pose[3:], degrees=False).as_matrix()

    T_base_to_end_effector = np.eye(4)
    T_base_to_end_effector[:3, :3] = orientation
    T_base_to_end_effector[:3, 3] = position

    # 计算物体相对于机械臂基座的位姿
    obj_camera_coordinates_homo = np.append(
        obj_camera_coordinates, [1]
    )  # 将物体坐标转换为齐次坐标
    # obj_end_effector_coordinates_homo = np.linalg.inv(T_camera_to_end_effector).dot(obj_camera_coordinates_homo)

    obj_end_effector_coordinates_homo = T_camera_to_end_effector.dot(
        obj_camera_coordinates_homo
    )

    obj_base_coordinates_homo = T_base_to_end_effector.dot(
        obj_end_effector_coordinates_homo
    )

    obj_base_coordinates = obj_base_coordinates_homo[
        :3
    ]  # 从齐次坐标中提取物体的x, y, z坐标

    # 组合结果，旋转保持原始的rx, ry, rz
    obj_base_pose = np.hstack((obj_base_coordinates, [rx, ry, rz]))

    return obj_base_pose



def vertical_catch(
        mask: ndarray = None,
        depth_frame: ndarray = None,
        color_intr: dict = None,
        current_pose: list = None,
        adjustment: list = None,       
        rotation_matrix: list = None,
        translation_vector: list = None,
        x: int = None,
        y: int = None
) -> Tuple[list, list, list]:
    """
    :param mask:    抓取物体的轮廓信息，如果为空则使用传入的x,y坐标
    :param depth_frame:     物体的深度值信息
    :param color_intr:      相机的内参
    :param current_pose:    当前的位姿信息
    :param adjustment:      夹爪安全预备位置和最终抓取位置的调整量
    :param rotation_matrix:         手眼标定的旋转矩阵
    :param translation_vector:      手眼标定的平移矩阵
    :param x: 如果mask为空，使用此x坐标
    :param y: 如果mask为空，使用此y坐标

    :return:
    above_object_pose：      垂直抓取物体上方的位姿
    correct_angle_pose：     垂直抓取物体正确的角度位姿
    finally_pose：           垂直抓取最终下爪的抓取位姿
    """

    if mask is not None and mask.size > 0:
        _, center = compute_angle_with_mask(mask)
        real_x, real_y = center[0], center[1]
        
        # 使用mask中的最大深度值
        depth_mask = depth_frame[mask == 255]
        non_zero_values = depth_mask[depth_mask != 0]
        if len(non_zero_values) > 0:
            dis = np.median(non_zero_values)
        else:
            # 如果没有有效的深度值，使用中心点的深度
            dis = depth_frame[real_y][real_x]
    else:
        # 使用传入的x,y坐标
        if x is None or y is None:
            raise ValueError("当mask为空时，必须提供x和y坐标")
        real_x, real_y = x, y
        # 使用指定点的深度信息
        dis = depth_frame[real_y][real_x]


    print("dis =  " ,dis)
    x = int(dis * (real_x - color_intr["ppx"]) / color_intr["fx"])
    y = int(dis * (real_y - color_intr["ppy"]) / color_intr["fy"])
    dis = int(dis)
    x, y, z = (
        (x) * 0.001,
        (y) * 0.001,
        (dis) * 0.001,
    )  # 夹爪刚好碰到 -180  前面加针 -200

    # 计算物体位置，位置是物体中心点正上方10公分
    obj_pose = convert(x, y, z, *current_pose, rotation_matrix, translation_vector)
    obj_pose = obj_pose.tolist() if hasattr(obj_pose, 'tolist') else list(obj_pose)

    

    computed_object_pose = obj_pose.copy()
    prepared_angle_pose = obj_pose.copy()
    finally_pose = obj_pose.copy()

    prepared_angle_pose[1] = obj_pose.copy()[1] - adjustment[0]
    prepared_angle_pose[3:] = current_pose[3:]
    finally_pose[1] =  obj_pose.copy()[1] - adjustment[1]
    finally_pose[3:] = current_pose[3:]


    # # 下潜距离
    # _z = min(obj_pose[2] * 0.8 + 0.10, 0.1 + 0.03)

    # # 最终位置为物体上方 + 夹爪 + 10cm的距离
    # obj_pose[2] = obj_pose.copy()[2] + 0.10 + arm_gripper_length * 0.001

    # # 修改为垂直于桌面的RX,RY,RZ``
    # obj_pose[3:] = vertical_rx_ry_rz   

    
    # correct_angle_pose = obj_pose.copy()

    # # 计算最终位姿
    # finally_pose = chage_pose(list(correct_angle_pose), _z)

    return computed_object_pose, prepared_angle_pose, finally_pose


def compute_angle_with_mask(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # 初始化最大外接矩形
    min_rect = None
    max_area = 0

    for contour in contours:
        # 计算最小外接矩形
        center, (w, h), angle = cv2.minAreaRect(contour)
        area = w * h
        if area > max_area:
            max_area = area
            min_rect = center, (w, h), angle

    # 获取最小外接矩形的信息
    center, (width, height), angle = min_rect

    if width > height:
        angle = -(90 - angle)
    else:
        angle = angle
    return angle, center