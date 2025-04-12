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
        init_api(app)
        
        # 添加根路由，服务前端页面
        @app.route('/')
        def serve_frontend():
            return send_from_directory(app.static_folder, 'index.html')
        
        @app.route('/<path:path>')
        def serve_static(path):
            return send_from_directory(app.static_folder, path)
        
        # 在应用上下文中初始化检测服务
        with app.app_context():
            app.logger.info('扫描可用模型...')
            available_models = detection_service.scan_available_models()
            
            if not available_models:
                app.logger.warning('未找到任何模型文件，请确保模型文件已放置在 backend/models 目录下')
            else:
                app.logger.info(f'找到 {len(available_models)} 个模型文件')
                for model_name, model_info in available_models.items():
                    app.logger.info(f'模型: {model_name}, 大小: {model_info["size"]}, 修改时间: {model_info["last_modified"]}')
                
                # 尝试加载默认模型
                app.logger.info('正在加载默认模型...')
                if detection_service.load_model():
                    app.logger.info('默认模型加载成功')
                else:
                    app.logger.error('默认模型加载失败')
            
        return app
        
    except Exception as e:
        app.logger.error(f'应用初始化失败: {str(e)}', exc_info=True)
        raise 