from openai import OpenAI
import os
import base64
import re
import json


def encode_image(image_path):
    """将图片编码为base64格式"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def detect_medicine_box(image_path, medicine_name, api_key=None, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"):
    """
    检测图片中指定药品盒的位置
    
    Args:
        image_path (str): 图片文件路径
        medicine_name (str): 要检测的药品名称
        api_key (str): API密钥，如果为None则从环境变量获取
        base_url (str): API基础URL
    
    Returns:
        list: [x, y] 坐标列表，检测不到返回[0, 0]
    """
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        print(f"错误：图片文件不存在 - {image_path}")
        return [0, 0]
    
    # 编码图片
    try:
        base64_image = encode_image(image_path)
    except Exception as e:
        print(f"错误：无法编码图片 - {e}")
        return [0, 0]
    
    # 获取API密钥
    if api_key is None:
        api_key = os.getenv('DASHSCOPE_API_KEY')
        if not api_key:
            print("错误：未设置DASHSCOPE_API_KEY环境变量")
            return [0, 0]
    
    # 设计优化的prompt
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

    # 创建客户端
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    try:
        # 调用API
        completion = client.chat.completions.create(
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
            temperature=0.1,  # 降低随机性，提高一致性
            max_tokens=100    # 限制输出长度
        )
        
        # 解析返回结果
        response_text = completion.choices[0].message.content.strip()
        
        # 尝试提取JSON格式的坐标
        try:
            # 查找JSON格式的坐标
            json_match = re.search(r'\{[^}]*"x"[^}]*"y"[^}]*\}', response_text)
            if json_match:
                json_str = json_match.group()
                coords = json.loads(json_str)
                x = int(coords.get('x', 0))
                y = int(coords.get('y', 0))
                return [x, y]
            
            # 如果没有找到JSON格式，尝试提取数字坐标
            numbers = re.findall(r'\d+', response_text)
            if len(numbers) >= 2:
                x = int(numbers[0])
                y = int(numbers[1])
                return [x, y]
            
            # 如果都没有找到，检查是否明确表示未找到
            if any(keyword in response_text.lower() for keyword in ['没有', '未找到', '不存在', 'none', 'not found']):
                return [0, 0]
            
            # 默认返回[0, 0]
            return [0, 0]
            
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            print(f"警告：无法解析返回结果 - {e}")
            print(f"原始返回：{response_text}")
            return [0, 0]
            
    except Exception as e:
        print(f"错误：API调用失败 - {e}")
        return [0, 0]


# 测试函数
def test_detection():
    """测试药品检测功能"""
    test_image = "/home/gml-cwl/code/robot2/data/test_images/camera_12_20250730_165750.jpg"
    medicine_name = "百合固今片"
    
    print(f"正在检测图片中的 '{medicine_name}'...")
    coordinates = detect_medicine_box(test_image, medicine_name)
    print(f"检测结果：{coordinates}")


if __name__ == "__main__":
    test_detection()