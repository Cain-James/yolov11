#!/usr/bin/env python3
import os
import sys
import time
import subprocess
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
        return False

def check_directories():
    """检查并创建必要的目录"""
    required_dirs = [
        Config.UPLOAD_FOLDER,
        os.path.dirname(Config.LOG_FILE)
    ]
    
    for directory in required_dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✓ 创建目录: {directory}")
            except Exception as e:
                print(f"✗ 创建目录失败 {directory}: {str(e)}")
                return False
        else:
            print(f"✓ 目录已存在: {directory}")
    
    return True

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

def check_and_fix_model_loading():
    """尝试预加载模型以避免首次API调用时加载慢的问题"""
    if not check_model_path() or not check_ultralytics():
        print("✗ 无法加载模型")
        return False
    
    try:
        from ultralytics import YOLO
        model_path = Config.MODEL_PATH
        print(f"\n预加载模型: {model_path}")
        model = YOLO(model_path)
        print("✓ 模型预加载成功!")
        
        # 创建模型状态标记文件
        status_file = os.path.join(root_dir, '.model_loaded')
        with open(status_file, 'w') as f:
            f.write(f"Model loaded successfully at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"✓ 创建模型状态标记文件: {status_file}")
        
        return True
    except Exception as e:
        print(f"✗ 预加载模型失败: {str(e)}")
        return False

def start_flask_service():
    """启动Flask服务"""
    print("\n正在启动Flask服务...")
    
    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"  # 确保Python输出不被缓存
    
    try:
        # 使用subprocess启动Flask应用
        process = subprocess.Popen(
            [sys.executable, "run.py"],
            cwd=root_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # 打印启动日志
        print("Flask服务正在启动，以下是日志输出:")
        print("-" * 60)
        
        # 读取并打印输出
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                
                # 检测服务是否已启动
                if "Running on" in output:
                    print("\n✓ Flask服务已成功启动!")
                    break
        
        # 检查进程是否已退出
        if process.poll() is not None:
            print(f"✗ Flask服务启动失败，退出代码: {process.returncode}")
            return False
            
        print("\n服务已在后台运行。按Ctrl+C停止。")
        return True
        
    except KeyboardInterrupt:
        print("\n用户中断，停止服务...")
        if process and process.poll() is None:
            process.terminate()
        return False
    except Exception as e:
        print(f"✗ 启动服务失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("检查系统并启动服务")
    print("=" * 60)
    
    # 检查模型和目录
    model_ok = check_model_path()
    dirs_ok = check_directories()
    ultralytics_ok = check_ultralytics()
    
    print("\n" + "-" * 60)
    
    # 预加载模型
    if model_ok and ultralytics_ok:
        model_loaded = check_and_fix_model_loading()
    else:
        print("✗ 无法预加载模型，请修复上述问题")
        model_loaded = False
    
    print("\n" + "-" * 60)
    
    # 启动服务，即使模型加载失败也尝试启动（API可以报告错误）
    if dirs_ok:
        start_flask_service()
    else:
        print("✗ 系统检查失败，无法启动服务")
    
    print("\n" + "=" * 60) 