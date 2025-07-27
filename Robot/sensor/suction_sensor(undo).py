# Robot/sensor/suction_sensor.py 
import serial
import sys
import threading
import time

# 串口配置
SERIAL_PORT = '/dev/ttyUSB0'  # 根据您的设备管理器确认正确的串口号
BAUD_RATE = 115200

# 气泵和气阀的ID
AIR_PUMP_ID = '000'
AIR_VALVE_ID = '001'

# 气泵指令
# 气泵最快速度吸气
AIR_PUMP_SUCK_COMMAND = f'#{AIR_PUMP_ID}P2500T0000!' 
# 气泵停止
AIR_PUMP_STOP_COMMAND = f'#{AIR_PUMP_ID}P1500T0000!'   

# 气阀指令
# 气阀关闭
AIR_VALVE_CLOSE_COMMAND = f'#{AIR_VALVE_ID}P1500T0000!' 
# 气阀打开
AIR_VALVE_OPEN_COMMAND = f'#{AIR_VALVE_ID}P2500T0000!'  

# 控制标志
running = True
air_pump_active = False

def serial_writer(ser):
    """
    负责向串口发送指令的线程
    """
    global air_pump_active
    while running:
        if air_pump_active:
            try:
                ser.write(AIR_PUMP_SUCK_COMMAND.encode())
                time.sleep(0.1)  # 避免发送过快
            except serial.SerialException as e:
                print(f"串口写入错误: {e}")
                break
        time.sleep(0.05) # 短暂延时，避免CPU占用过高

def keyboard_listener(ser):
    """
    负责监听键盘输入的线程
    """
    global running, air_pump_active
    print("按 'q' 关闭气阀, 'w' 打开气阀, 'e' 退出程序并停止吸气。")
    
    # 初始状态：气泵停止，气阀关闭
    try:
        ser.write(AIR_PUMP_STOP_COMMAND.encode())
        ser.write(AIR_VALVE_CLOSE_COMMAND.encode())
        print("气泵已停止，气阀已关闭。")
    except serial.SerialException as e:
        print(f"初始化串口写入错误: {e}")
        running = False
        return

    air_pump_active = True # 启动时开始吸气
    print("气泵已启动吸气。")

    while running:
        try:
            key = sys.stdin.read(1)
            if key == 'q':
                ser.write(AIR_VALVE_CLOSE_COMMAND.encode())
                print("气阀已关闭。")
            elif key == 'w':
                ser.write(AIR_VALVE_OPEN_COMMAND.encode())
                print("气阀已打开。")
            elif key == 'e':
                running = False
                air_pump_active = False
                ser.write(AIR_PUMP_STOP_COMMAND.encode()) # 停止吸气
                ser.write(AIR_VALVE_CLOSE_COMMAND.encode()) # 关闭气阀
                print("退出程序。气泵已停止，气阀已关闭。")
            else:
                pass
        except Exception as e:
            print(f"键盘输入错误: {e}")
            running = False

def main():
    global running
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"成功连接到串口 {SERIAL_PORT} @ {BAUD_RATE} 波特率。")
    except serial.SerialException as e:
        print(f"无法连接到串口 {SERIAL_PORT}: {e}")
        print("请检查串口是否正确连接，或者是否有权限访问该串口 (例如：sudo chmod 666 /dev/ttyUSB0)")
        return

    # 启动串口写入线程
    writer_thread = threading.Thread(target=serial_writer, args=(ser,))
    writer_thread.daemon = True  # 设置为守护线程，主线程退出时自动终止
    writer_thread.start()

    # 启动键盘监听线程
    listener_thread = threading.Thread(target=keyboard_listener, args=(ser,))
    listener_thread.daemon = True
    listener_thread.start()

    # 保持主线程运行，直到接收到退出指令
    while running:
        time.sleep(0.5)

    writer_thread.join(timeout=1) # 等待线程结束
    listener_thread.join(timeout=1) # 等待线程结束
    ser.close()
    print("串口已关闭。")

if __name__ == "__main__":
    main()