import serial
import threading
import time

class SuctionController:
    """
    吸盘控制器，支持吸、松开、关闭和状态读取。
    """
    # 指令ID
    AIR_PUMP_ID = '000'
    AIR_VALVE_ID = '001'
    # 指令
    AIR_PUMP_SUCK_COMMAND = f'#{AIR_PUMP_ID}P2500T0000!'
    AIR_PUMP_STOP_COMMAND = f'#{AIR_PUMP_ID}P1500T0000!'
    AIR_VALVE_CLOSE_COMMAND = f'#{AIR_VALVE_ID}P1500T0000!'
    AIR_VALVE_OPEN_COMMAND = f'#{AIR_VALVE_ID}P2500T0000!'

    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.status = 'close'  # 状态: suck, release, close
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
        except serial.SerialException as e:
            print(f"串口连接失败: {e}")
            self.ser = None
        self._lock = threading.Lock()

    def suck(self):
        """吸气"""
        with self._lock:
            if self.ser:
                self.ser.write(self.AIR_PUMP_SUCK_COMMAND.encode())
                self.ser.write(self.AIR_VALVE_CLOSE_COMMAND.encode())
                self.status = 'suck'

    def release(self):
        """松开（打开气阀）"""
        with self._lock:
            if self.ser:
                self.ser.write(self.AIR_VALVE_OPEN_COMMAND.encode())
                self.status = 'release'

    def close(self):
        """关闭（气泵停止，气阀关闭）"""
        with self._lock:
            if self.ser:
                self.ser.write(self.AIR_PUMP_STOP_COMMAND.encode())
                self.ser.write(self.AIR_VALVE_CLOSE_COMMAND.encode())
                self.status = 'close'

    def get_status(self):
        """获取当前状态"""
        return self.status

    def __del__(self):
        if self.ser:
            self.ser.close() 