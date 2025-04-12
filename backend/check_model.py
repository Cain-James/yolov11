#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = script_dir  # backend目录
sys.path.insert(0, root_dir)

# 导入配置
from config.config import Config

def check_model_path():
    """检查模型文件路径是否正确"""
    model_path = Config.MODEL_PATH
    print(f"配置的模型路径: {model_path}")
    
    if os.path.exists(model_path):
        print(f"✓ 模型文件存在")
        file_size = os.path.getsize(model_path) / (1024 * 1024)  # 转换为MB
        print(f"✓ 模型文件大小: {file_size:.2f} MB")
        return True
    else:
        print(f"✗ 模型文件不存在!")
        
        # 检查上级目录是否存在
        parent_dir = os.path.dirname(model_path)
        if os.path.exists(parent_dir):
            print(f"✓ 父目录存在: {parent_dir}")
            print(f"目录内容:")
            for item in os.listdir(parent_dir):
                item_path = os.path.join(parent_dir, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path) / (1024 * 1024)  # 转换为MB
                    print(f"  - {item} ({size:.2f} MB)")
                else:
                    print(f"  - {item}/ (目录)")
        else:
            print(f"✗ 父目录不存在: {parent_dir}")
            
            # 尝试创建目录结构
            try:
                os.makedirs(parent_dir, exist_ok=True)
                print(f"√ 已创建父目录: {parent_dir}")
            except Exception as e:
                print(f"✗ 创建父目录失败: {str(e)}")
        
        return False

def check_ultralytics():
    """检查ultralytics库是否正确安装"""
    try:
        from ultralytics import YOLO
        print("✓ ultralytics库已安装")
        return True
    except ImportError:
        print("✗ ultralytics库未安装")
        return False
    except Exception as e:
        print(f"✗ 导入ultralytics时出错: {str(e)}")
        return False

def search_model_files():
    """在项目目录中搜索可能的模型文件"""
    print("\n搜索项目中的模型文件...")
    model_files = []
    
    # 定义要搜索的扩展名
    extensions = ['.pt', '.pth', '.weights']
    
    # 从项目根目录开始搜索
    project_root = os.path.dirname(root_dir)
    for root, dirs, files in os.walk(project_root):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_root)
                size = os.path.getsize(full_path) / (1024 * 1024)  # 转换为MB
                model_files.append((rel_path, size))
    
    if model_files:
        print(f"找到 {len(model_files)} 个可能的模型文件:")
        for path, size in model_files:
            print(f"  - {path} ({size:.2f} MB)")
        
        # 提示如何更新配置
        print("\n如果要使用上述文件之一，请修改 config/config.py 中的 MODEL_PATH 配置:")
        print("示例: MODEL_PATH = os.path.join(ROOT_DIR, '文件相对于项目根目录的路径')")
    else:
        print("未找到任何可能的模型文件")

def test_load_model():
    """尝试加载模型"""
    if not check_model_path() or not check_ultralytics():
        print("✗ 无法加载模型")
        return False
    
    try:
        from ultralytics import YOLO
        model_path = Config.MODEL_PATH
        print(f"\n尝试加载模型: {model_path}")
        model = YOLO(model_path)
        print("✓ 模型加载成功!")
        return True
    except Exception as e:
        print(f"✗ 加载模型失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("模型状态检查工具")
    print("=" * 60)
    
    check_model_path()
    print("\n" + "-" * 60)
    check_ultralytics()
    print("\n" + "-" * 60)
    
    # 尝试加载模型
    if not test_load_model():
        # 如果加载失败，搜索可能的模型文件
        search_model_files()
    
    print("\n" + "=" * 60) 