import json
import cv2
import os
from ollama import Client

path = 'logs/20250813_002823_left_rgb.jpg'
client = Client()
message=[
        {
            'role': 'system',
            'content': """你是一个专业的药品检测助手。你的任务是：
1. 仔细分析图片中的药品盒
2. 识别指定的药品名称
3. 如果找到目标药品盒，计算其边界框坐标（左上角和右下角）
4. 严格按照指定格式返回结果

重要规则：
- 坐标系统：图片左上角为原点(0,0)，向右为x轴正方向，向下为y轴正方向
- 返回格式：不要用markdown格式，严禁用代码块格式，必须严格按照纯文本JSON格式返回，例如：{"x1": 200, "y1": 150, "x2": 500, "y2": 350}
- 如果未找到目标药品，返回：{"x1": 0, "y1": 0, "x2": 0, "y2": 0}
- 不要添加任何多余文字，只返回JSON格式的纯文本""",           
        },
        {

            'role': 'user',
            'content': '请在图片中精确找到药品:氨咖黄敏胶囊',
            'images': [path],
        }
        
    ]
#氨咖黄敏胶囊维C银翘片蒲地蓝消炎口服液复方氨酚烷胺胶囊
response = client.chat(
    model='qwen2.5vl:32b',
    messages=message,
)

# 获取响应内容
result = response.message.content
print(f"API返回结果: {result}")

try:
    # 解析JSON结果
    bbox = json.loads(result)
    
    # 读取原始图像
    image = cv2.imread(path)
    if image is None:
        print(f"无法读取图像: {path}")
        exit(1)
    
    # 检查是否找到药品
    if bbox["x1"] == 0 and bbox["y1"] == 0 and bbox["x2"] == 0 and bbox["y2"] == 0:
        print("未找到目标药品")
    else:
        # 在图像上绘制边界框
        x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # 添加标签
        cv2.putText(image, "氨咖黄敏胶囊", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    
    # 保存结果图像
    output_dir = os.path.dirname(path)
    output_path = os.path.join(output_dir, "result_with_bbox.jpg")
    cv2.imwrite(output_path, image)
    print(f"已保存结果图像到: {output_path}")
    
except json.JSONDecodeError:
    print(f"无法解析JSON结果: {result}")
except Exception as e:
    print(f"处理过程中出错: {str(e)}")