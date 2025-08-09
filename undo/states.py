from enum import Enum, auto
from typing import Optional, Dict, Callable

class GraspState(Enum):
    """抓取任务的状态枚举"""
    PRESCRIPTION_DISPLAY = auto()    # 展示处方并等待用户确认
    PRESCRIPTION_RECOGNITION = auto() # 处方识别状态
    MEDICINE_SELECTION = auto()      # 选择当前要抓取的药品
    POINT_SELECTION = auto()         # 点选择状态
    SEGMENTATION = auto()            # 分割状态
    GRASPING = auto()               # 抓取状态
    RESETTING = auto()              # 复位状态
    FINISHED = auto()               # 完成状态
    ERROR = auto()                  # 错误状态（表示任何阶段发生不可恢复的错误）

class StateMachine:
    """状态机管理器"""
    def __init__(self, logger):
        self.current_state = GraspState.PRESCRIPTION_DISPLAY
        self.logger = logger
        self.error_info = None  # 记录错误信息
        
        # 状态处理器字典
        self.state_handlers: Dict[GraspState, Callable] = {}
        
        # 状态转换字典：{当前状态: {结果: 下一个状态}}
        self.state_transitions = {
            GraspState.PRESCRIPTION_DISPLAY: {
                True: GraspState.PRESCRIPTION_RECOGNITION,  # 用户确认处方准备就绪
                False: GraspState.ERROR                    # 显示出错
            },
            GraspState.PRESCRIPTION_RECOGNITION: {
                True: GraspState.MEDICINE_SELECTION,       # 识别成功
                False: GraspState.ERROR                    # 识别失败
            },
            GraspState.MEDICINE_SELECTION: {
                True: GraspState.POINT_SELECTION,         # 还有药品需要处理
                False: GraspState.FINISHED                # 所有药品处理完成
            },
            GraspState.POINT_SELECTION: {
                True: GraspState.SEGMENTATION,
                False: GraspState.MEDICINE_SELECTION    # 选点失败，尝试下一个药品
            },
            GraspState.SEGMENTATION: {
                True: GraspState.GRASPING,
                False: GraspState.POINT_SELECTION  # 分割失败，重新选点
            },
            GraspState.GRASPING: {
                True: GraspState.RESETTING,
                False: GraspState.POINT_SELECTION  # 抓取失败，重新选点
            },
            GraspState.RESETTING: {
                True: GraspState.MEDICINE_SELECTION,  # 完成一个药品，继续下一个
                False: GraspState.ERROR              # 复位失败
            },
            GraspState.FINISHED: {
                True: GraspState.PRESCRIPTION_DISPLAY,  # 开始新的处方
                False: None                            # 结束程序
            },
            GraspState.ERROR: {
                True: None,    # 错误状态总是导致程序结束
                False: None    # 错误状态总是导致程序结束
            }
        }

    def register_handler(self, state: GraspState, handler: Callable) -> None:
        """注册状态处理器"""
        self.state_handlers[state] = handler

    def transition(self, success: bool) -> Optional[GraspState]:
        """状态转换"""
        if self.current_state not in self.state_transitions:
            return None
        
        next_state = self.state_transitions[self.current_state].get(success)        
      
        if next_state:
            self.logger.info(f"状态转换: {self.current_state.name} -> {next_state.name}")
            self.current_state = next_state
        
        return next_state

    def run(self) -> bool:
        """运行当前状态的处理器"""
        if self.current_state not in self.state_handlers:
            self.logger.error(f"未找到状态 {self.current_state.name} 的处理器")
            return False
        
        handler = self.state_handlers[self.current_state]
        return handler()
