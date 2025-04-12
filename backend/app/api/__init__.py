from flask import Blueprint, jsonify, request
from .detection import detection_bp
from ..services.detection import detection_service

def init_api(app):
    # 创建主API蓝图
    api_bp = Blueprint('api', __name__)
    
    # 注册子蓝图
    api_bp.register_blueprint(detection_bp, url_prefix='/api')
    
    # 添加当前模型信息路由
    @api_bp.route('/models/current', methods=['GET'])
    def get_current_model():
        try:
            status = detection_service.get_model_status()
            return jsonify({
                'success': True,
                'data': {
                    'current_model': status.get('current_model'),
                    'is_loaded': status.get('loaded', False)
                }
            })
        except Exception as e:
            app.logger.error(f"获取当前模型信息时出错: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"获取当前模型信息失败: {str(e)}"
            }), 500
    
    # 注册API蓝图
    app.register_blueprint(api_bp, url_prefix='/api')