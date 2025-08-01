#!/usr/bin/env python3

import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grasp_task.grasp_task import main

if __name__ == "__main__":
    main() 