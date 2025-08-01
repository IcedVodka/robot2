#!/usr/bin/env python3
"""
下载SAM模型权重
"""

from ultralytics import SAM
import os

def download_sam_models():
    """下载所有SAM模型"""
    models = ['sam_b.pt', 'sam_l.pt', 'sam_h.pt']
    
    print("SAM模型权重信息:")
    print("=" * 50)
    print("1. sam_b.pt - Base model (358MB) - 基础模型，速度快，精度一般")
    print("2. sam_l.pt - Large model (1.2GB) - 大模型，平衡速度和精度")
    print("3. sam_h.pt - Huge model (2.4GB) - 超大模型，最高精度，速度较慢")
    print()
    
    print("推荐使用 sam_l.pt 用于大多数应用场景")
    print("当前你使用的是 sam_b.pt，如果效果不好，建议升级到 sam_l.pt")
    print()
    
    # 下载sam_l.pt（推荐模型）
    print("正在下载 sam_l.pt (推荐模型)...")
    try:
        model = SAM('sam_l.pt')
        print("✅ sam_l.pt 下载成功!")
        print(f"模型保存在: {model.ckpt_path}")
        return True
    except Exception as e:
        print(f"❌ sam_l.pt 下载失败: {e}")
        return False

if __name__ == "__main__":
    download_sam_models() 