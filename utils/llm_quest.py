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
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        """
        初始化视觉API类
        
        Args:
            api_key: API密钥，如果为None则从环境变量获取
            base_url: API基础URL
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

    def _call_vision_api(self, image_input: ImageInput, system_prompt: str, user_prompt: str, max_tokens: int = 100 , temperature = 0.1) -> str:
        """
        调用视觉API
        
        Args:
            image_input: 图像输入数据
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            max_tokens: 最大token数
            
        Returns:
            str: API响应文本
        """
        try:
            base64_image = self._encode_image(image_input)
            
            completion = self.client.chat.completions.create(
                model="qwen-vl-max-latest",
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

    def detect_medicine_box(self, image_input: ImageInput, medicine_name: str) -> Tuple[int, int]:
        """
        检测图片中指定药品盒的位置
        
        Args:
            image_input: 图像输入数据
            medicine_name: 要检测的药品名称
            
        Returns:
            Tuple[int, int]: (x, y) 坐标元组，检测不到返回(0, 0)
        """
        try:
            self._validate_image_input(image_input)
            
            system_prompt = """你是一个专业的药品检测助手。你的任务是：
1. 仔细分析图片中的药品盒
2. 识别指定的药品名称
3. 如果找到目标药品盒，计算其中心点坐标
4. 严格按照指定格式返回结果

重要规则：
- 坐标系统：图片左上角为原点(0,0)，向右为x轴正方向，向下为y轴正方向
- 坐标范围：x和y都应该是0到1000之间的整数
- 返回格式：必须严格按照JSON格式返回，例如：{"x": 500, "y": 300}
- 如果未找到目标药品，返回：{"x": 0, "y": 0}
- 不要添加任何解释文字，只返回JSON格式的坐标"""

            user_prompt = f"""请检测图片中是否存在"{medicine_name}"这个药品盒。

如果找到了，请返回该药品盒中心点的坐标，格式为JSON：
{{"x": x坐标, "y": y坐标}}

如果没有找到，请返回：
{{"x": 0, "y": 0}}

注意：
- 坐标值应该是0-1000之间的整数
- 只返回JSON格式，不要添加其他文字
- 确保坐标是药品盒的中心点位置"""

            # 调用API获取响应
            response_text = self._call_vision_api(image_input, system_prompt, user_prompt, max_tokens=100)
            
            # 尝试提取JSON格式的坐标
            try:
                # 查找JSON格式的坐标
                json_match = re.search(r'\{[^}]*"x"[^}]*"y"[^}]*\}', response_text)
                if json_match:
                    json_str = json_match.group()
                    coords = json.loads(json_str)
                    x = int(coords.get('x', 0))
                    y = int(coords.get('y', 0))
                    return (x, y)
                
                # 如果没有找到JSON格式，尝试提取数字坐标
                numbers = re.findall(r'\d+', response_text)
                if len(numbers) >= 2:
                    x = int(numbers[0])
                    y = int(numbers[1])
                    return (x, y)
                
                # 如果都没有找到，检查是否明确表示未找到
                if any(keyword in response_text.lower() for keyword in ['没有', '未找到', '不存在', 'none', 'not found']):
                    return (0, 0)
                
                # 默认返回(0, 0)
                return (0, 0)
                
            except (json.JSONDecodeError, ValueError, IndexError) as e:
                print(f"警告：无法解析返回结果 - {e}")
                print(f"原始返回：{response_text}")
                return (0, 0)
                
        except Exception as e:
            print(f"错误：{str(e)}")
            return (0, 0)


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
            
            system_prompt = """你是一个专业的医疗处方单识别助手。你的任务是：
1. 仔细分析处方单图片中的所有药品名称
2. 提取所有药品名称并以JSON列表格式返回
3. 不需要包含用量、用法等信息，只需要药品名称

重要规则：
- 只返回药品名称列表
- 必须严格按照JSON格式返回，例如：["药品1", "药品2", "药品3"]
- 不要添加任何解释文字，只返回JSON格式的列表"""

            user_prompt = """请识别处方单中的所有药品名称，并以JSON列表格式返回。

格式要求：
["药品1", "药品2", "药品3"]

注意：
- 只需要返回药品名称
- 不需要包含剂量、用法等信息
- 只返回JSON格式，不要添加其他文字"""

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


