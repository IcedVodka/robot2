## to do list
重构了项目框架

### 测试任务
    普通相机rgb_camera.py
        深度相机depth_camera.py
    机器人操控信息读取realman_controller.py
    手臂遥操跟随arm_teleop.py
    完成吸盘的改写

    模型解耦：将YOLO和SAM分别封装为独立模块，放到policy/models/下。
    窗口管理独立：所有窗口和交互统一用utils/window_manager管理。
    相机模块化：所有相机采集逻辑用Robot/sensor/下的传感器类统一管理，暴露统一接口。
    主流程只做业务调度，不处理底层细节。


手势检测手部控制遥操