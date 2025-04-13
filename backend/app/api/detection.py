from flask import Blueprint, request, jsonify, current_app
from backend.app.core.security import require_auth
from backend.app.services.detection import detection_service
import os
import gc

detection_bp = Blueprint('detection', __name__)

@detection_bp.route('/detect', methods=['POST'])
def detect():
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'data': {
                    'detections': [],
                    'class_counts': {},
                    'message': '未找到上传的文件'
                }
            }), 400
        
        file = request.files['file']
        if not file:
            return jsonify({
                'success': False,
                'data': {
                    'detections': [],
                    'class_counts': {},
                    'message': '文件为空'
                }
            }), 400
        
        # 获取可选的模型路径参数
        model_path = request.form.get('model_path')
        
        # 保存上传的文件
        import tempfile
        import os
        
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        
        try:
            # 处理图片
            result = detection_service.process_image(temp_path, model_path)
            return jsonify(result)
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        
    except Exception as e:
        current_app.logger.error(f"检测过程出错: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'data': {
                'detections': [],
                'class_counts': {},
                'message': f"检测失败: {str(e)}"
            }
        }), 500

@detection_bp.route('/analyze', methods=['POST'])
# @require_auth  # 暂时注释掉鉴权
def analyze():
    """处理图片分析请求"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有上传文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'})
    
    try:
        result = detection_service.analyze_image(file)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@detection_bp.route('/detect', methods=['POST'])
# @require_auth  # 暂时注释掉鉴权
def switch_model():
    """切换模型"""
    try:
        # 获取请求参数
        data = request.get_json()
        if not data or 'model_name' not in data:
            return jsonify({
                'success': False,
                'error': '缺少模型名称参数'
            }), 400
        
        model_name = data['model_name']
        
        # 检查模型是否存在
        status = detection_service.get_model_status()
        available_models = status.get('available_models', {})
        if model_name not in available_models:
            return jsonify({
                'success': False,
                'error': f'模型 {model_name} 不存在'
            }), 404
        
        # 获取模型路径
        model_path = available_models[model_name]['path']
        
        # 切换模型
        success = detection_service.switch_model(model_path)
        if success:
            return jsonify({
                'success': True,
                'message': f'已切换到模型: {model_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': '切换模型失败'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"切换模型时出错: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'切换模型失败: {str(e)}'
        }), 500