from flask import Flask, send_from_directory
from flask_cors import CORS
from backend.config.config import Config
from backend.app.api import init_api
from backend.app.services.detection import detection_service
import logging
from logging.handlers import RotatingFileHandler
import os

def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__, static_folder='../../frontend/dist', static_url_path='')
    
    # 配置跨域
    CORS(app)
    
    # 加载配置
    app.config.from_object(Config)
    
    # 注册API蓝图
    from .api import init_api
    api_bp = init_api(app)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    try:
        # 配置日志
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        file_handler = RotatingFileHandler(
            'logs/backend.log',
            maxBytes=10240,
            backupCount=10
        )
        
        # 使用Config中定义的日志格式和级别
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('应用启动')
        
        # 初始化应用配置
        Config.init_app(app)
        
        # 初始化API路由
        # init_api(app)
        
        # 添加根路由，服务前端页面
        @app.route('/')
        def serve_frontend():
            return send_from_directory(app.static_folder, 'index.html')
        
        @app.route('/<path:path>')
        def serve_static(path):
            return send_from_directory(app.static_folder, path)
        
        # 在应用上下文中初始化检测服务
        with app.app_context():
            app.logger.info('正在加载默认模型...')
            if detection_service.load_model():
                app.logger.info('默认模型加载成功')
            else:
                app.logger.error('默认模型加载失败，请检查模型文件是否正确')
            
        return app
        
    except Exception as e:
        app.logger.error(f'应用初始化失败: {str(e)}', exc_info=True)
        raise