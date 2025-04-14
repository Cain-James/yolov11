import os
from pathlib import Path
import logging

# 基础路径配置
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
print("当前目录：" + BASE_DIR)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

# 确保上传文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Flask应用配置
class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    DEBUG = True
    
    # 路径配置
    BASE_DIR = BASE_DIR
    ROOT_DIR = os.path.dirname(BASE_DIR)  # 获取项目根目录
    MODEL_DIR = os.path.join(BASE_DIR, 'models')  # 模型目录
    
    # 确保模型目录存在
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # 单一模型配置
    MODEL_PATH = os.path.join(MODEL_DIR, 'best.pt')
    
    UPLOAD_FOLDER = UPLOAD_FOLDER
    LOG_FILE = os.path.join(BASE_DIR, 'logs', 'app.log')
    
    # API配置
    API_PREFIX = '/api'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 限制上传大小为50MB
    
    
    # 硅基流动API配置
    SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY') or "sk-njosapcjncszdpwwwydlmixtsapjmvwnoohaeigaabkhwlgy"
    SILICONFLOW_API_URL = os.environ.get('SILICONFLOW_API_URL') or "https://api.siliconflow.com/v1/chat/completions"
    
    # 日志配置
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 创建必要的目录
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(os.path.dirname(Config.LOG_FILE), exist_ok=True)
        
        # 配置日志
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # 配置文件上传
        app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
        app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH 