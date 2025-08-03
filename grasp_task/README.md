# Grasp Task 模块

基于处方的机械臂抓取系统，使用大模型视觉API进行处方识别和目标选择，结合SAM分割模型实现精确抓取。

## 功能特性

- **处方识别**: 使用千问视觉API自动识别处方中的药品信息
- **智能选点**: 基于大模型自动选择抓取目标点
- **精确分割**: 使用SAM模型进行目标分割
- **状态机管理**: 完整的状态机实现，确保任务流程的可靠性
- **机械臂控制**: 集成RealMan机械臂进行精确抓取

## 系统架构

### 状态机实现逻辑

系统采用状态机模式管理整个抓取流程，包含以下状态：

1. **PRESCRIPTION_DISPLAY**: 展示处方并等待用户确认
2. **PRESCRIPTION_RECOGNITION**: 使用千问API识别处方内容
3. **MEDICINE_SELECTION**: 根据处方的药品清单选择下一个要抓取的药品
4. **POINT_SELECTION**: 使用大模型自动选择抓取点
5. **SEGMENTATION**: 使用SAM模型进行目标分割
6. **GRASPING**: 执行机械臂抓取动作
7. **RESETTING**: 机械臂复位到安全位置，之后跳转到 MEDICINE_SELECTION 
8. **FINISHED**: 完成一张处方，之后跳转到 PRESCRIPTION_DISPLAY 开启新一轮大的循环
9. **ERROR**: 错误处理状态



## 环境配置

### 1. 千问API配置

1. 访问 [千问开放平台](https://dashscope.aliyun.com/) 注册账号
2. 申请视觉API权限
3. 获取API Key
4. 设置环境变量：

```bash
export DASHSCOPE_API_KEY="your_api_key_here"
```

或在 `~/.bashrc` 中添加：
```bash
echo 'export DASHSCOPE_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

### 2. 依赖安装

```bash
pip install opencv-python numpy openai dashscope
```

### 3. 硬件配置

- **相机**: RealSense深度相机
- **机械臂**: RealMan机械臂
- **SAM模型**: 确保 `assets/weights/sam_b.pt` 文件存在

## 使用方法

### 基本使用

```bash
# 直接运行
python run_grasp_task.py

# 或者进入grasp_task目录运行
cd grasp_task
python grasp_task.py
```

### 配置参数

在 `config.py` 中修改相关配置：

```python
class GraspConfig:
    def __init__(self):
        # 相机参数
        self.camera_serial = "327122072195"  # 修改为你的相机序列号
        
        # 机械臂参数
        self.robot_ip = "192.168.1.18"      # 修改为你的机械臂IP
        self.robot_port = 8080
        
        # SAM模型路径
        self.sam_model_path = "/path/to/sam_b.pt"
```

## 工作流程

### 1. 处方展示阶段
- 系统提示用户将处方放在摄像头下方
- 自动捕获处方图像
- 等待用户确认

### 2. 处方识别阶段
- 使用千问视觉API识别处方内容
- 提取药品名称列表
- 验证识别结果

### 3. 药品选择阶段
- 从处方中依次选择下一个要抓取的药品
- 当所有药品处理完成时，进入完成状态

### 4. 点选择阶段
- 使用大模型分析当前场景
- 自动选择目标药品的最佳抓取点
- 支持手动选点模式（可选）

### 5. 分割阶段
- 使用SAM模型基于选定的点进行目标分割
- 生成精确的目标掩码
- 计算抓取位置

### 6. 抓取阶段
- 机械臂移动到计算出的抓取位置
- 执行抓取动作
- 验证抓取结果

### 7. 复位阶段
- 机械臂回到安全位置
- 准备下一个药品的抓取

## 模块说明

### 核心模块

- **`grasp_task.py`**: 主任务类，协调各个模块
- **`states.py`**: 状态机实现，管理任务流程
- **`config.py`**: 配置参数管理
- **`llm_quest.py`**: 千问API封装，处理视觉识别
- **`image_handler.py`**: 图像处理模块
- **`point_selector.py`**: 点选择模块
- **`robot_control.py`**: 机械臂控制模块
- **`prescription_handler.py`**: 处方处理模块

### 关键功能

#### 视觉API调用
```python
from grasp_task.llm_quest import VisionAPI

# 初始化API
api = VisionAPI()

# 识别处方
medicines = api.extract_prescription_medicines(image_input)

# 检测药品位置
x, y = api.detect_medicine_box(image_input, medicine_name)
```

#### 状态机使用
```python
from grasp_task.states import StateMachine, GraspState

# 创建状态机
state_machine = StateMachine(logger)

# 注册状态处理器
state_machine.register_handler(GraspState.POINT_SELECTION, handler_function)

# 运行状态机
while state_machine.current_state != GraspState.ERROR:
    result = state_machine.run()
    next_state = state_machine.transition(result)
```

## 故障排除

### 常见问题

1. **API Key未设置**
   ```
   ValueError: 未设置API密钥
   ```
   解决：确保设置了 `DASHSCOPE_API_KEY` 环境变量

2. **相机连接失败**
   ```
   Camera initialization failed
   ```
   解决：检查相机连接和序列号配置

3. **机械臂连接失败**
   ```
   Robot connection failed
   ```
   解决：检查机械臂IP地址和网络连接

4. **SAM模型文件不存在**
   ```
   FileNotFoundError: SAM model not found
   ```
   解决：确保 `sam_b.pt` 文件在正确路径下

### 调试模式

启用详细日志：
```python
from utils.logger import setup_logger
setup_logger(log_level=logging.DEBUG, enable_color=True)
```

## 扩展开发

### 添加新的状态处理器

```python
def custom_handler():
    # 自定义处理逻辑
    return True  # 成功返回True，失败返回False

# 注册处理器
state_machine.register_handler(GraspState.CUSTOM_STATE, custom_handler)
```

### 修改状态转换逻辑

在 `states.py` 中修改 `state_transitions` 字典：

```python
self.state_transitions = {
    GraspState.CURRENT_STATE: {
        True: GraspState.NEXT_STATE_SUCCESS,
        False: GraspState.NEXT_STATE_FAILURE
    }
}
```

## 许可证

本项目遵循 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。 