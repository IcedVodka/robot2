#!/usr/bin/env python3

import sys
import os
import time

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grasp_task2.grasp_task import GraspTask

if __name__ == "__main__":
    
    grasp_task = GraspTask()
    grasp_task.right_robot.suck()
    time.sleep(2)
    grasp_task.right_robot.release_suck()
    time.sleep(2)
    grasp_task.left_robot.suck()
    time.sleep(2)
    grasp_task.left_robot.release_suck()
    time.sleep(2)
