import cv2
import numpy as np
from numpy import ndarray
from typing import Tuple
import copy
from .convert import convert
from .crawl import chage_pose


def center_compute_pose(
        depth_frame: ndarray,
        color_intr: dict,
        current_pose: list,
        adjustment: list,
        point: list,
        rotation_matrix: list,
        translation_vector: list,
) -> Tuple[list, list, list]:

    real_x, real_y = point[0], point[1]   
    dis = depth_frame[real_y][real_x]    

    x = int(dis * (real_x - color_intr["ppx"]) / color_intr["fx"])
    y = int(dis * (real_y - color_intr["ppy"]) / color_intr["fy"])
    dis = int(dis)
    x, y, z = (
        (x) * 0.001,
        (y) * 0.001,
        (dis) * 0.001,
    )  

    # 计算物体位置，位置是物体中心点正上方10公分
    obj_pose = convert(x, y, z, *current_pose, rotation_matrix, translation_vector)
    obj_pose = obj_pose.tolist() if hasattr(obj_pose, 'tolist') else list(obj_pose)
    

    computed_object_pose = obj_pose.copy()
    prepared_angle_pose = obj_pose.copy()
    finally_pose = obj_pose.copy()

    prepared_angle_pose[0] = obj_pose.copy()[0] + adjustment[0]
    prepared_angle_pose[3:] = current_pose[3:]
    finally_pose[0] =  obj_pose.copy()[0] + adjustment[1]
    finally_pose[3:] = current_pose[3:]

    return computed_object_pose, prepared_angle_pose, finally_pose

