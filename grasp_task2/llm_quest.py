from openai import OpenAI
import os
import base64
import re
import json
from typing import List, Dict, Union, Optional, Tuple
from dataclasses import dataclass

import cv2
import numpy as np

@dataclass
class ImageInput:
    """图像输入数据类
    
    Args:
        image_path: JPG图片文件路径，必须是.jpg或.jpeg格式
        image_np: OpenCV捕获的图像数据，必须为BGR格式，将被编码为JPG格式
    """
    image_path: Optional[str] = None
    image_np: Optional[np.ndarray] = None

class VisionAPI:
    """视觉API封装类"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "http://localhost:11434/v1"):
        """
        初始化视觉API类
        
        Args:
            api_key: API密钥，如果为None则从环境变量获取
            base_url: API基础URL
            base_url: str = "http://localhost:11434/v1"
            base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        """
        self.api_key = api_key or os.getenv('DASHSCOPE_API_KEY')
        if not self.api_key:
            raise ValueError("未设置API密钥")
        
        self.base_url = base_url
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _encode_image(self, image_input: ImageInput) -> str:
        """
        将图片编码为base64格式
        
        Args:
            image_input: 图像输入数据
            
        Returns:
            str: base64编码的图片数据
        """
        if image_input.image_np is not None:
            # image_np 必须为BGR格式，否则颜色会异常
            _, buffer = cv2.imencode('.jpg', image_input.image_np)
            return base64.b64encode(buffer).decode("utf-8")
        elif image_input.image_path is not None:
            with open(image_input.image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        else:
            raise ValueError("必须提供 image_path 或 image_np")


    def _validate_image_input(self, image_input: ImageInput) -> None:
        """
        验证图像输入
        
        Args:
            image_input: 图像输入数据
        """
        if image_input.image_np is None and image_input.image_path is None:
            raise ValueError("必须提供 image_path 或 image_np")
        
        # 验证numpy数组输入
        if image_input.image_np is not None and not isinstance(image_input.image_np, np.ndarray):
            raise ValueError("image_np 必须为 numpy.ndarray")
            
        # 验证图片路径输入
        if image_input.image_path is not None:
            # 检查文件是否存在
            if not os.path.exists(image_input.image_path):
                raise FileNotFoundError(f"图片文件不存在 - {image_input.image_path}")
            
            # 检查文件扩展名
            ext = os.path.splitext(image_input.image_path)[1].lower()
            if ext not in ['.jpg', '.jpeg']:
                raise ValueError(f"图片必须是JPG格式 (当前格式: {ext})")

    def _call_vision_api(self, image_input: ImageInput, system_prompt: str, user_prompt: str, model = "qwen2.5vl:7b", max_tokens: int = 100 , temperature = 0.1) -> str:
        """
        调用视觉API
        
        Args:
            image_input: 图像输入数据
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            model:模型名称 "qwen-vl-max-latest","qwen2.5vl:7b"
            max_tokens: 最大token数
            
        Returns:
            str: API响应文本
        """
        try:
            base64_image = self._encode_image(image_input)
            
            completion = self.client.chat.completions.create(
                model= model,
                messages=[
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": system_prompt}]
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            },
                            {"type": "text", "text": user_prompt}
                        ]
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return completion.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"API调用失败: {str(e)}")

    def detect_medicine_box(self, image_input: ImageInput, medicine_name: str) -> List[int]:
        """
        检测图片中指定药品盒的位置
        
        Args:
            image_input: 图像输入数据
            medicine_name: 要检测的药品名称
            
        Returns:
            List[int]: [x1, y1, x2, y2] 坐标列表，表示目标检测框的左上角和右下角坐标，检测不到返回[0, 0, 0, 0]
        """
        try:
            self._validate_image_input(image_input)
            
            system_prompt = """你是一个专业的药品检测助手。你的任务是：
1. 仔细分析图片中的药品盒
2. 识别指定的药品名称
3. 如果找到目标药品盒，计算其边界框坐标（左上角和右下角）
4. 严格按照指定格式返回结果

重要规则：
- 坐标系统：图片左上角为原点(0,0)，向右为x轴正方向，向下为y轴正方向
- 坐标范围：所有坐标值都应该是0到1000之间的整数
- 返回格式：必须严格按照JSON格式返回，例如：{"x1": 200, "y1": 150, "x2": 500, "y2": 350}
- 如果未找到目标药品，返回：{"x1": 0, "y1": 0, "x2": 0, "y2": 0}
- 不要添加任何解释文字，只返回JSON格式的坐标"""

            user_prompt = f"""请检测图片中是否存在"{medicine_name}"这个药品盒。

如果找到了，请返回该药品盒的边界框坐标，格式为JSON：
{{"x1": 左上角x坐标, "y1": 左上角y坐标, "x2": 右下角x坐标, "y2": 右下角y坐标}}

如果没有找到，请返回：
{{"x1": 0, "y1": 0, "x2": 0, "y2": 0}}

注意：
- 坐标值应该是0-1000之间的整数
- 只返回JSON格式，不要添加其他文字
- 确保坐标准确表示药品盒的边界"""

            # 调用API获取响应
            response_text = self._call_vision_api(image_input, system_prompt, user_prompt, max_tokens=100)
            
            # 尝试提取JSON格式的坐标
            try:
                # 查找JSON格式的坐标
                json_match = re.search(r'\{[^}]*"x1"[^}]*"y1"[^}]*"x2"[^}]*"y2"[^}]*\}', response_text)
                if json_match:
                    json_str = json_match.group()
                    coords = json.loads(json_str)
                    x1 = int(coords.get('x1', 0))
                    y1 = int(coords.get('y1', 0))
                    x2 = int(coords.get('x2', 0))
                    y2 = int(coords.get('y2', 0))
                    return [x1, y1, x2, y2]
                
                # 如果没有找到JSON格式，尝试提取数字坐标
                numbers = re.findall(r'\d+', response_text)
                if len(numbers) >= 4:
                    x1 = int(numbers[0])
                    y1 = int(numbers[1])
                    x2 = int(numbers[2])
                    y2 = int(numbers[3])
                    return [x1, y1, x2, y2]
                
                # 如果都没有找到，检查是否明确表示未找到
                if any(keyword in response_text.lower() for keyword in ['没有', '未找到', '不存在', 'none', 'not found']):
                    return [0, 0, 0, 0]
                
                # 默认返回[0, 0, 0, 0]
                return [0, 0, 0, 0]
                
            except (json.JSONDecodeError, ValueError, IndexError) as e:
                print(f"警告：无法解析返回结果 - {e}")
                print(f"原始返回：{response_text}")
                return [0, 0, 0, 0]
                
        except Exception as e:
            print(f"错误：{str(e)}")
            return [0, 0, 0, 0]


    def extract_prescription_medicines(self, image_input: ImageInput) -> List[str]:
        """
        从处方单图片中提取药品列表
        
        Args:
            image_input: 图像输入数据
            
        Returns:
            List[str]: 药品名称列表，如果识别失败返回空列表
        """
        try:
            self._validate_image_input(image_input)
            
            system_prompt = """你是一个专业的处方单识别助手。请从处方图片中提取药品名称列表并严格按以下规则输出：

- 仅提取药品名称本身（保留原字面，不含规格、剂型、剂量、包装信息，例如 “0.8g*32片”“8g”“10ml”“盒/支/瓶”等）。
- 忽略“用法/用量/频次/途径”等说明行（例如以“用法：”开头的行）。
- 按数量展开：若药品后出现数量（例如 “2盒”“×2”“*2”“2支”“2瓶”“2包”“2贴”等），则将该药品名称重复输出相应次数；未出现数量时视为 1。
- 按处方出现顺序输出（在数量展开后仍保持顺序）。
- 只输出严格的 JSON 字符串数组，例如：["健胃消食片","红霉素软膏","红霉素软膏"]。
- 不要输出任何解释或额外文字；无法识别时输出 []。"""

            user_prompt = """请从图中的处方单提取药品名称，并按上述规则返回严格的 JSON 数组（仅名称，按数量展开）。示例：

输入文本示意：
R: 1. 健胃消食片 0.8g*32片 1盒
用法：1日3次，1次3片
2. 红霉素软膏 8g 2盒
用法：1日2次，涂于患处

期望输出：
["健胃消食片","红霉素软膏","红霉素软膏"]

请只返回 JSON 数组。"""

            # 调用API获取响应
            response_text = self._call_vision_api(image_input, system_prompt, user_prompt, max_tokens=500)
            
            try:
                # 尝试直接解析JSON
                return json.loads(response_text)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取方括号中的内容
                matches = re.search(r'\[(.*?)\]', response_text)
                if matches:
                    # 分割字符串并清理每个药品名称
                    medicines = [med.strip(' "\'') for med in matches.group(1).split(',')]
                    return medicines
                return []
                
        except Exception as e:
            print(f"错误：{str(e)}")
            return []


