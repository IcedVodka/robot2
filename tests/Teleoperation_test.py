from Robot.RealmanController import RealmanController, TeleoperationController
from utils.debug_print import debug_print
import time

if __name__ == "__main__":
    master = RealmanController("Master")
    slave = RealmanController("Slave")
    master.set_up("192.168.1.19", 8080)  # 修改为你的 master 机械臂 IP
    slave.set_up("192.168.1.18", 8080)   # 修改为你的 slave 机械臂 IP
    master.set_init_joint()
    slave.set_init_joint()
    time.sleep(3)
    teleop = TeleoperationController(master, slave, fps=100)
    teleop.start()
    try:
        import sys
        import termios
        import tty
        debug_print("Main", "按 q 抓取，e 松开，z 退出...", "INFO")
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        while True:
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch.lower() == 'z':
                    debug_print("Main", "退出遥操作...", "INFO")
                    break
                elif ch.lower() == 'q':
                    teleop.set_hand_state('grip')
                    debug_print("Main", "[主控] 设置灵巧手为夹紧", "INFO")
                elif ch.lower() == 'e':
                    teleop.set_hand_state('open')
                    debug_print("Main", "[主控] 设置灵巧手为松开", "INFO")
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        time.sleep(0.1)
    except KeyboardInterrupt:
        debug_print("Main", "\n手动中断", "INFO")
    teleop.stop()
