import os

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit
    
    # 模型配置
    MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'best.pt')
    TOWER_CRANE_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'tower_crane.pt')
    OTHER_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'other.pt')
    
    # 硅基流动API配置
    SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY')
    SILICONFLOW_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
    
    # 确保上传目录存在
    @staticmethod
    def init_app(app):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True) 