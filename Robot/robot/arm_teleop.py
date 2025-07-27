"""
关节映射遥操作
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional
import yaml
from utils.logger import get_logger
from typing import Optional
import threading
import queue
import time
from realman_controller import RealmanController  


def load_teleop_config(path="configs/teleoperate.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["teleoperation"]


class ArmJointFollower:
    """
    机械臂本体关节主从跟随控制器
    实现主从机械臂的关节实时跟随。
    """
    def __init__(self, master: RealmanController, slave: RealmanController, fps: int = 30):
        self.master = master
        self.slave = slave
        self.fps = fps
        self._q = queue.Queue(maxsize=10)
        self._running = False
        self._master_thread: Optional[threading.Thread] = None
        self._slave_thread: Optional[threading.Thread] = None
        self.logger = get_logger("ArmJointFollower")

    @classmethod
    def from_config(cls, config_path: str = "configs/teleoperate.yaml", fps: int = 30):
        cfg = load_teleop_config(config_path)
        master = RealmanController(cfg["master"]["name"])
        slave = RealmanController(cfg["slave"]["name"])
        master.set_up(cfg["master"]["ip"], cfg["master"]["port"])
        slave.set_up(cfg["slave"]["ip"], cfg["slave"]["port"])
        return cls(master, slave, fps)

    def _collect_master_joints(self):
        interval = 1.0 / self.fps
        while self._running:
            try:
                state = self.master.get_state()
                joint = state["joint"]
                self._q.put(joint, timeout=0.1)
                self.logger.debug(f"采集到主臂关节数据: {joint}")
            except Exception as e:
                self.logger.error(f"[Master] 采集关节出错: {e}")
            time.sleep(interval)

    def _apply_slave_joints(self):
        while self._running:
            try:
                joint = self._q.get(timeout=0.5)
                self.slave.set_arm_joints(joint)
                self.logger.debug(f"设置从臂关节数据: {joint}")
            except queue.Empty:
                pass
            except Exception as e:
                self.logger.error(f"[Slave] 设置关节出错: {e}")

    def start(self):
        self._running = True
        self._master_thread = threading.Thread(target=self._collect_master_joints)
        self._slave_thread = threading.Thread(target=self._apply_slave_joints)
        self._master_thread.start()
        self._slave_thread.start()
        self.logger.info("机械臂主从关节跟随已启动")

    def stop(self):
        self._running = False
        if self._master_thread:
            self._master_thread.join()
        if self._slave_thread:
            self._slave_thread.join()
        self.logger.info("机械臂主从关节跟随已停止") 