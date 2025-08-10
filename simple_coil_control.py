#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版：向线圈0的地址0发送0或1

这个示例专门展示如何：
1. 连接机械臂
2. 配置末端RS485为Modbus RTU主站
3. 向设备1的线圈0发送0或1
4. 读取线圈状态验证

使用方法：
python simple_coil_control.py
"""

import time
from Robotic_Arm.rm_robot_interface import RoboticArm
from Robotic_Arm.rm_ctypes_wrap import rm_peripheral_read_write_params_t

def main():
    """主函数 - 向线圈0发送0或1"""
    
    # 机械臂连接参数
    ROBOT_IP = "192.168.1.18"  # 请根据实际情况修改
    ROBOT_PORT = 8080
    
    # Modbus参数
    DEVICE_ADDRESS = 1      # 设备地址
    COIL_ADDRESS = 0        # 线圈地址
    BAUDRATE = 9600         # 波特率
    TIMEOUT = 10            # 超时时间（百毫秒）
    
    robot_arm = None
    
    try:
        print("=== 睿尔曼机械臂线圈控制示例 ===")
        print(f"目标：向设备{DEVICE_ADDRESS}的线圈{COIL_ADDRESS}发送0或1")
        print()
        
        # 1. 创建并连接机械臂
        print("1. 连接机械臂...")
        robot_arm = RoboticArm()
        ret = robot_arm.rm_create_robot_arm(ip=ROBOT_IP, port=ROBOT_PORT, level=3)
        
        if ret != 0:
            print(f"✗ 连接失败，错误码：{ret}")
            return
        
        print("✓ 机械臂连接成功")
        
        # 2. 配置末端RS485为Modbus RTU主站模式
        print("\n2. 配置Modbus RTU主站模式...")
        ret = robot_arm.rm_set_modbus_mode(
            port=1,  # 末端接口板RS485接口
            baudrate=BAUDRATE,
            timeout=TIMEOUT
        )
        
        if ret != 0:
            print(f"✗ Modbus配置失败，错误码：{ret}")
            return
        
        print("✓ Modbus RTU主站模式配置成功")
        
        # 等待配置生效
        print("\n等待配置生效...")
        time.sleep(2)
        
        # 3. 向线圈0发送1
        print("\n3. 向线圈0发送值：1")
        write_params = rm_peripheral_read_write_params_t(
            port=1,           # 末端接口板RS485接口
            address=COIL_ADDRESS,  # 线圈地址0
            device=DEVICE_ADDRESS, # 设备地址1
            num=1             # 写入1个线圈
        )
        
        ret = robot_arm.rm_write_single_coil(write_params, 1)
        if ret == 0:
            print("✓ 线圈0写入1成功")
        else:
            print(f"✗ 线圈写入失败，错误码：{ret}")
            return
        
        # 4. 读取线圈0状态验证
        print("\n4. 读取线圈0状态验证...")
        read_params = rm_peripheral_read_write_params_t(
            port=1,           # 末端接口板RS485接口
            address=COIL_ADDRESS,  # 线圈地址0
            device=DEVICE_ADDRESS, # 设备地址1
            num=1             # 读取1个线圈
        )
        
        ret, coil_value = robot_arm.rm_read_coils(read_params)
        if ret == 0:
            print(f"✓ 线圈0当前值：{coil_value}")
        else:
            print(f"✗ 线圈读取失败，错误码：{ret}")
        
        time.sleep(2)
        
        # 5. 向线圈0发送0
        print("\n5. 向线圈0发送值：0")
        ret = robot_arm.rm_write_single_coil(write_params, 0)
        if ret == 0:
            print("✓ 线圈0写入0成功")
        else:
            print(f"✗ 线圈写入失败，错误码：{ret}")
            return
        
        # 6. 再次读取线圈0状态验证
        print("\n6. 再次读取线圈0状态验证...")
        ret, coil_value = robot_arm.rm_read_coils(read_params)
        if ret == 0:
            print(f"✓ 线圈0当前值：{coil_value}")
        else:
            print(f"✗ 线圈读取失败，错误码：{ret}")
        
        # 7. 关闭Modbus模式
        print("\n7. 关闭Modbus模式...")
        ret = robot_arm.rm_close_modbus_mode(port=1)
        if ret == 0:
            print("✓ Modbus模式已关闭")
        else:
            print(f"✗ 关闭Modbus模式失败，错误码：{ret}")
        
        print("\n=== 操作完成 ===")
        
    except Exception as e:
        print(f"✗ 程序执行异常：{e}")
    
    finally:
        # 断开机械臂连接
        if robot_arm:
            print("\n断开机械臂连接...")
            robot_arm.rm_delete_robot_arm()
            print("✓ 连接已断开")

if __name__ == "__main__":
    main()
