#!/usr/bin/env python3
"""
下载SAM模型权重
"""

import os
import time
import requests
from pathlib import Path
from ultralytics import SAM
import hashlib

def get_file_hash(file_path):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def download_with_retry(url, file_path, max_retries=3):
    """带重试机制的下载函数"""
    for attempt in range(max_retries):
        try:
            print(f"尝试下载 {url} (第 {attempt + 1} 次)")
            
            # 使用requests下载
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r下载进度: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
            
            print(f"\n✅ 下载完成: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ 下载失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print("所有重试都失败了")
                return False
    
    return False

def download_sam_models():
    """下载所有SAM模型"""
    models_info = {
        'sam_b.pt': {
            'url': 'https://github.com/ultralytics/assets/releases/download/v8.3.0/sam_b.pt',
            'size': '358MB',
            'desc': '基础模型，速度快，精度一般'
        },
        'sam_l.pt': {
            'url': 'https://github.com/ultralytics/assets/releases/download/v8.3.0/sam_l.pt',
            'size': '1.2GB',
            'desc': '大模型，平衡速度和精度'
        },
        'sam_h.pt': {
            'url': 'https://github.com/ultralytics/assets/releases/download/v8.3.0/sam_h.pt',
            'size': '2.4GB',
            'desc': '超大模型，最高精度，速度较慢'
        }
    }
    
    print("SAM模型权重信息:")
    print("=" * 50)
    for i, (model_name, info) in enumerate(models_info.items(), 1):
        print(f"{i}. {model_name} - {info['size']} - {info['desc']}")
    print()
    
    print("推荐使用 sam_l.pt 用于大多数应用场景")
    print("当前你使用的是 sam_b.pt，如果效果不好，建议升级到 sam_l.pt")
    print()
    
    # 检查当前目录
    current_dir = Path.cwd()
    print(f"当前工作目录: {current_dir}")
    
    # 尝试下载sam_l.pt（推荐模型）
    model_name = 'sam_l.pt'
    model_info = models_info[model_name]
    
    print(f"正在下载 {model_name} (推荐模型)...")
    print(f"下载URL: {model_info['url']}")
    
    # # 方法1: 使用requests直接下载
    # print("\n方法1: 使用requests直接下载...")
    # if download_with_retry(model_info['url'], model_name):
    #     print("✅ 直接下载成功!")
        
    #     # 验证文件完整性
    #     print("验证文件完整性...")
    #     try:
    #         model = SAM(model_name)
    #         print(f"✅ 模型加载成功! 模型保存在: {model.ckpt_path}")
    #         return True
    #     except Exception as e:
    #         print(f"❌ 模型加载失败: {e}")
    #         print("文件可能损坏，尝试重新下载...")
    #         if os.path.exists(model_name):
    #             os.remove(model_name)
    
    # # 方法2: 使用ultralytics自动下载
    # print("\n方法2: 使用ultralytics自动下载...")
    # try:
    #     print("正在使用ultralytics下载...")
    #     model = SAM(model_name)
    #     print("✅ ultralytics下载成功!")
    #     print(f"模型保存在: {model.ckpt_path}")
    #     return True
    # except Exception as e:
    #     print(f"❌ ultralytics下载失败: {e}")
    
    # 方法3: 尝试下载较小的模型
    print("\n方法3: 尝试下载较小的sam_b.pt模型...")
    try:
        print("正在下载sam_b.pt...")
        model = SAM('sam_b.pt')
        print("✅ sam_b.pt下载成功!")
        print(f"模型保存在: {model.ckpt_path}")
        return True
    except Exception as e:
        print(f"❌ sam_b.pt下载也失败: {e}")
    
    print("\n所有下载方法都失败了。请检查:")
    print("1. 网络连接是否正常")
    print("2. 是否有足够的磁盘空间")
    print("3. 防火墙是否阻止了下载")
    print("4. 可以尝试手动下载模型文件")
    
    return False

if __name__ == "__main__":
    download_sam_models() 