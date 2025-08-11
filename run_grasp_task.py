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
    grasp_task.single_medicine_grasp("蒲地蓝消炎口服液", arm_side="left",use_sam= False)
    # grasp_task.single_medicine_grasp("复方氨酚烷胺胶囊", arm_side="right",use_sam= False)