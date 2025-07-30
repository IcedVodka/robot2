import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Robot.sensor.suction_sensor import SuctionController

def keyboard_control_suction(suction):
    """
    键盘控制吸盘功能
    's' - 吸气
    'r' - 松开
    'c' - 关闭
    'q' - 退出
    """
    print("=== 吸盘键盘控制 ===")
    print("按键说明:")
    print("  's' - 吸气")
    print("  'r' - 松开") 
    print("  'c' - 关闭")
    print("  'q' - 退出程序")
    print("==================")
    
    while True:
        try:
            cmd = input("请输入命令 (s/r/c/q): ").lower().strip()
            
            if cmd == 's':
                print("执行: 吸气")
                suction.suck()
                print(f"当前状态: {suction.get_status()}")
            elif cmd == 'r':
                print("执行: 松开")
                suction.release()
                print(f"当前状态: {suction.get_status()}")
            elif cmd == 'c':
                print("执行: 关闭")
                suction.close()
                print(f"当前状态: {suction.get_status()}")
            elif cmd == 'q':
                print("退出程序...")
                break
            else:
                print("无效命令，请重新输入")
                
        except KeyboardInterrupt:
            print("\n程序被中断")
            break

if __name__ == "__main__":
    # 初始化吸盘控制器
    suction = SuctionController()
    
    # 检查串口连接
    if suction.ser is None:
        print("错误: 无法连接到吸盘控制器，请检查串口连接")
        exit(1)
    
    print("吸盘控制器初始化成功")
    print(f"当前状态: {suction.get_status()}")
    
    # 启动键盘控制
    keyboard_control_suction(suction) 