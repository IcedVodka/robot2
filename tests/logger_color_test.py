#!/usr/bin/env python3
"""
测试带颜色的日志输出
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger, get_logger


def test_colored_logger():
    """测试带颜色的日志输出"""
    print("=" * 60)
    print("测试带颜色的日志输出")
    print("=" * 60)
    
    # 启用颜色输出
    setup_logger(enable_color=True)
    
    # 获取不同模块的logger
    sensor_logger = get_logger("Sensor.RGB_Camera")
    robot_logger = get_logger("Robot.Controller")
    module_logger = get_logger("Module.HandDetection")
    test_logger = get_logger("Test.ColorDemo")
    
    print("\n--- 不同级别的日志输出 ---")
    test_logger.debug("这是DEBUG级别的日志（青色）")
    test_logger.info("这是INFO级别的日志（绿色）")
    test_logger.warning("这是WARNING级别的日志（黄色）")
    test_logger.error("这是ERROR级别的日志（红色）")
    test_logger.critical("这是CRITICAL级别的日志（紫色）")
    
    print("\n--- 不同模块的日志输出 ---")
    sensor_logger.info("RGB相机初始化成功")
    robot_logger.warning("机械臂连接超时，尝试重连...")
    module_logger.error("手势检测模块加载失败")
    sensor_logger.debug("传感器数据: [1, 2, 3, 4]")
    
    print("\n--- 禁用颜色输出测试 ---")
    # 重新设置logger，禁用颜色
    setup_logger(enable_color=False)
    
    test_logger = get_logger("Test.NoColor")
    test_logger.info("这是禁用颜色后的INFO日志")
    test_logger.warning("这是禁用颜色后的WARNING日志")
    test_logger.error("这是禁用颜色后的ERROR日志")


def check_terminal_support():
    """检查终端是否支持颜色"""
    print("\n" + "=" * 60)
    print("终端颜色支持检查")
    print("=" * 60)
    
    # 检查是否在终端中运行
    if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        print("✓ 检测到终端环境")
    else:
        print("✗ 未检测到终端环境（可能在IDE中运行）")
    
    # 检查环境变量
    import os
    term = os.environ.get('TERM', '')
    print(f"终端类型: {term}")
    
    # 检查是否支持颜色
    if 'color' in term.lower() or 'xterm' in term.lower():
        print("✓ 终端可能支持颜色")
    else:
        print("? 终端颜色支持未知")
    
    # 测试ANSI颜色代码
    print("\nANSI颜色测试:")
    colors = {
        '青色': '\033[36m',
        '绿色': '\033[32m', 
        '黄色': '\033[33m',
        '红色': '\033[31m',
        '紫色': '\033[35m',
        '重置': '\033[0m'
    }
    
    for name, code in colors.items():
        if name != '重置':
            print(f"{code}这是{name}文本{colors['重置']}")
        else:
            print(f"{code}重置颜色{colors['重置']}")


if __name__ == "__main__":
    # 检查终端支持
    check_terminal_support()
    
    # 测试带颜色的日志
    test_colored_logger()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60) 