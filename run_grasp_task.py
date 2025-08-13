#!/usr/bin/env python3

import sys
import os
import time
from utils.logger import setup_logger, get_logger


# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grasp_task2.grasp_task import GraspTask


if __name__ == "__main__":
    grasp_task = GraspTask()
    grasp_task.place_medicine_basket()
    # grasp_task.single_medicine_grasp("硫酸氢氯吡格雷片", arm_side="right")


    



    # # grasp_task.left_robot.suck()
    # # grasp_task.right_robot.suck()
    # # grasp_task.single_medicine_grasp("维c银翘片", arm_side="left")
    # # grasp_task.single_medicine_grasp("复方氨酚烷胺片", arm_side="left",use_sam= False)
    # # grasp_task.single_medicine_grasp("氨咖黄敏胶囊", arm_side="right",use_sam= False)

    # 右臂 [-4.129000186920166, 86.25, -93.26100158691406, -71.06600189208984, -89.21800231933594, 181.88800048828125]

    # 左臂 [-164.67799377441406, -84.99700164794922, 86.07499694824219, 57.44200134277344, 92.0530014038086, -2.1019999980926514]