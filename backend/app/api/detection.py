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

@detection_bp.route('/model/status', methods=['GET'])
# @require_auth  # 暂时注释掉鉴权
def model_status():
    """获取模型状态"""
    try:
        status = detection_service.get_model_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@detection_bp.route('/model_status', methods=['GET'])
# @require_auth  # 暂时注释掉鉴权
def model_status_alias():
    """获取模型状态（别名）"""
    return model_status()

@detection_bp.route('/model/switch', methods=['POST'])
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

@detection_bp.route('/reset_model', methods=['POST'])
# @require_auth  # 暂时注释掉鉴权
def reset_model():
    """重置模型状态（供调试使用）"""
    try:
        # 重置模型状态
        if detection_service.model_loaded:
            # 关闭当前模型
            detection_service.model = None
            detection_service.model_loaded = False
            
            # 尝试删除状态标记文件
            status_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.model_loaded')
            if os.path.exists(status_file):
                os.remove(status_file)
            
            # 尝试手动触发垃圾回收
            gc.collect()
            
            return jsonify({
                'success': True,
                'message': '模型状态已重置，下次API调用将重新加载模型'
            })
        else:
            return jsonify({
                'success': True,
                'message': '模型未加载，无需重置'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'重置模型状态失败: {str(e)}'
        })

@detection_bp.route('/test_model_loading', methods=['GET'])
# @require_auth
def test_model_loading():
    """测试模型加载（供调试使用）"""
    try:
        # 清理旧状态（可选）
        was_loaded = detection_service.model_loaded
        if was_loaded:
            detection_service.model = None
            detection_service.model_loaded = False
            import gc
            gc.collect()
        
        # 记录开始时间
        import time
        start_time = time.time()
        
        # 记录详细日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info("开始测试模型加载...")
        
        # 获取模型路径
        from flask import current_app
        model_path = current_app.config['MODEL_PATH']
        logger.info(f"模型路径: {model_path}")
        
        # 检查文件是否存在
        import os
        if not os.path.exists(model_path):
            return jsonify({
                'success': False,
                'error': f'模型文件不存在: {model_path}'
            })
        
        # 获取文件大小
        file_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
        logger.info(f"模型文件大小: {file_size:.2f} MB")
        
        # 加载模型
        try:
            # 直接尝试加载
            from ultralytics import YOLO
            model = YOLO(model_path)
            
            # 检查模型是否加载成功
            if model is None:
                return jsonify({
                    'success': False,
                    'error': '模型加载失败，结果为None'
                })
            
            # 检查模型属性
            model_names = model.names
            classes_count = len(model_names)
            
            # 计算加载耗时
            end_time = time.time()
            load_time = end_time - start_time
            
            # 更新服务实例
            detection_service.model = model
            detection_service.model_loaded = True
            
            return jsonify({
                'success': True,
                'message': f'模型加载成功，耗时 {load_time:.2f} 秒',
                'model_info': {
                    'classes_count': classes_count,
                    'model_path': model_path,
                    'file_size_mb': file_size,
                    'was_previously_loaded': was_loaded
                }
            })
            
        except Exception as e:
            import traceback
            error_details = str(e)
            stack_trace = traceback.format_exc()
            logger.error(f"直接加载模型失败: {error_details}")
            logger.error(f"错误堆栈: {stack_trace}")
            
            return jsonify({
                'success': False,
                'error': f'模型加载失败: {error_details}',
                'traceback': stack_trace
            })
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': f'测试失败: {str(e)}',
            'traceback': traceback.format_exc()
        })

@detection_bp.route('/check_model', methods=['GET'])
def check_model():
    """直接检查模型状态和尝试加载模型"""
    import os
    import logging
    import time
    import traceback
    from flask import current_app
    from ultralytics import YOLO
    
    logger = logging.getLogger(__name__)
    
    try:
        # 记录开始时间
        start_time = time.time()
        logger.info("开始检查模型状态...")
        
        # 获取模型路径
        model_path = current_app.config['MODEL_PATH']
        logger.info(f"模型路径: {model_path}")
        
        # 检查文件是否存在
        if not os.path.exists(model_path):
            return jsonify({
                'success': False,
                'loaded': False,
                'error': f'模型文件不存在: {model_path}'
            })
        
        # 获取文件信息
        file_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
        logger.info(f"模型文件大小: {file_size:.2f} MB")
        
        # 检查模型格式
        valid_extensions = ['.pt', '.pth', '.weights']
        file_ext = os.path.splitext(model_path)[1].lower()
        if file_ext not in valid_extensions:
            return jsonify({
                'success': False,
                'loaded': False,
                'error': f'模型文件格式不正确: {file_ext}，应为 {valid_extensions}'
            })
        
        # 检查当前模型加载状态
        current_status = detection_service.model_loaded
        logger.info(f"当前模型加载状态: {'已加载' if current_status else '未加载'}")
        
        # 如果已经加载，直接返回成功
        if current_status and detection_service.model is not None:
            return jsonify({
                'success': True,
                'loaded': True,
                'message': '模型已加载，无需重新加载',
                'model_path': model_path
            })
        
        # 尝试加载模型
        try:
            logger.info("尝试使用YOLO直接加载模型...")
            # 直接尝试加载YOLO模型
            model = YOLO(model_path)
            
            # 检查模型是否加载成功
            if model is None:
                return jsonify({
                    'success': False,
                    'loaded': False,
                    'error': '模型加载失败，结果为None'
                })
            
            # 检查模型属性
            try:
                model_names = model.names
                classes_count = len(model_names)
                logger.info(f"模型包含 {classes_count} 个类别")
            except Exception as attr_err:
                logger.warning(f"获取模型属性出错: {str(attr_err)}")
                classes_count = "未知"
            
            # 计算加载耗时
            end_time = time.time()
            load_time = end_time - start_time
            
            # 更新服务实例
            detection_service.model = model
            detection_service.model_loaded = True
            
            return jsonify({
                'success': True,
                'loaded': True,
                'message': f'模型加载成功，耗时 {load_time:.2f} 秒',
                'model_info': {
                    'classes_count': classes_count,
                    'model_path': model_path,
                    'file_size_mb': f"{file_size:.2f}"
                }
            })
            
        except Exception as e:
            error_details = str(e)
            stack_trace = traceback.format_exc()
            logger.error(f"加载模型失败: {error_details}")
            logger.error(f"错误堆栈: {stack_trace}")
            
            # 尝试获取更多系统信息
            sys_info = {}
            try:
                import platform
                sys_info['platform'] = platform.platform()
                sys_info['python'] = platform.python_version()
                
                try:
                    import torch
                    sys_info['torch'] = torch.__version__
                    sys_info['cuda_available'] = torch.cuda.is_available() if hasattr(torch, 'cuda') else False
                    if sys_info['cuda_available']:
                        sys_info['cuda_version'] = torch.version.cuda if hasattr(torch.version, 'cuda') else "未知"
                        sys_info['gpu_name'] = torch.cuda.get_device_name(0) if hasattr(torch.cuda, 'get_device_name') else "未知"
                except ImportError:
                    sys_info['torch'] = "未安装"
                    
                try:
                    import psutil
                    mem = psutil.virtual_memory()
                    sys_info['total_memory'] = f"{mem.total / (1024**3):.2f} GB"
                    sys_info['available_memory'] = f"{mem.available / (1024**3):.2f} GB"
                except ImportError:
                    sys_info['memory_info'] = "无法获取"
            except Exception as sys_err:
                sys_info['error'] = str(sys_err)
            
            return jsonify({
                'success': False,
                'loaded': False,
                'error': f'模型加载失败: {error_details}',
                'system_info': sys_info
            })
            
    except Exception as e:
        logger.exception(f"检查模型状态时出错: {str(e)}")
        return jsonify({
            'success': False,
            'loaded': False,
            'error': f'系统错误: {str(e)}'
        }) 