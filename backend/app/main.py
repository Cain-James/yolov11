from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from flask_cors import CORS
import os
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io
import base64
import logging
import threading
import time
import requests
import json
from ..services.detection import detection_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),  # 文件处理器
        logging.StreamHandler()  # 控制台处理器
    ]
)
logger = logging.getLogger(__name__)

# 创建蓝图
main_bp = Blueprint('main', __name__)

# 全局变量存储模型和加载状态
model = None
model_loaded = False
model_load_error = None

# 英文类别名称到中文的映射
CLASS_MAPPING = {
    "person": "人",
    "bicycle": "自行车",
    "car": "汽车",
    "motorcycle": "摩托车",
    "airplane": "飞机",
    "bus": "公交车",
    "train": "火车",
    "truck": "卡车",
    "boat": "船",
    "traffic light": "交通灯",
    "fire hydrant": "消防栓",
    "stop sign": "停止标志",
    "parking meter": "停车计时器",
    "bench": "长椅",
    "bird": "鸟",
    "cat": "猫",
    "dog": "狗",
    "horse": "马",
    "sheep": "羊",
    "cow": "牛",
    "elephant": "大象",
    "bear": "熊",
    "zebra": "斑马",
    "giraffe": "长颈鹿",
    "backpack": "背包",
    "umbrella": "雨伞",
    "handbag": "手提包",
    "tie": "领带",
    "suitcase": "手提箱",
    "frisbee": "飞盘",
    "skis": "滑雪板",
    "snowboard": "滑雪板",
    "sports ball": "运动球",
    "kite": "风筝",
    "baseball bat": "棒球棒",
    "baseball glove": "棒球手套",
    "skateboard": "滑板",
    "surfboard": "冲浪板",
    "tennis racket": "网球拍",
    "bottle": "瓶子",
    "wine glass": "酒杯",
    "cup": "杯子",
    "fork": "叉子",
    "knife": "刀",
    "spoon": "勺子",
    "bowl": "碗",
    "banana": "香蕉",
    "apple": "苹果",
    "sandwich": "三明治",
    "orange": "橙子",
    "broccoli": "西兰花",
    "carrot": "胡萝卜",
    "hot dog": "热狗",
    "pizza": "披萨",
    "donut": "甜甜圈",
    "cake": "蛋糕",
    "chair": "椅子",
    "couch": "沙发",
    "potted plant": "盆栽植物",
    "bed": "床",
    "dining table": "餐桌",
    "toilet": "厕所",
    "tv": "电视",
    "laptop": "笔记本电脑",
    "mouse": "鼠标",
    "remote": "遥控器",
    "keyboard": "键盘",
    "cell phone": "手机",
    "microwave": "微波炉",
    "oven": "烤箱",
    "toaster": "烤面包机",
    "sink": "水槽",
    "refrigerator": "冰箱",
    "book": "书",
    "clock": "时钟",
    "vase": "花瓶",
    "scissors": "剪刀",
    "teddy bear": "泰迪熊",
    "hair drier": "吹风机",
    "toothbrush": "牙刷",
    # CAD2024自定义类别
    "Crane": "起重机",
    "Dormitory": "宿舍",
    "Excavator": "挖掘机",
    "Gate": "大门",
    "Mixer": "搅拌机",
    "Office": "办公室",
    "Red_Line": "红线",
    "Road": "道路",
    "Stairs": "楼梯",
    "Steel_processing": "钢筋加工厂",
    "Tower_Crane": "塔吊",
    "toilet": "厕所"
}

# 硅基流动API配置
SILICONFLOW_API_KEY = "sk-njosapcjncszdpwwwydlmixtsapjmvwnoohaeigaabkhwlgy"
SILICONFLOW_API_URL = "https://api.siliconflow.com/v1/chat/completions"

def analyze_image_with_siliconflow(image_base64):
    """使用硅基流动API分析图片"""
    try:
        headers = {
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "model": "deepseek-ai/deepseek-vl2",
            "temperature": 0.7,
            "top_p": 0.95,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的建筑图纸分析专家，擅长识别和分析建筑图纸中的各种元素。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请详细分析这张建筑图纸，可以参考图纸的文字说明、图注等，分析的输出需要包括：主要建筑元素（塔吊[一般用圆圈表示]、大门、办公室、堆场、厕所、道路、挖掘机、推土机、起重机或其它工程器械等的位置和数量，并分析塔吊是否覆盖了一些主要建筑，和其他一些有用的关系"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
        }
        
        logger.info("正在发送API请求...")
        response = requests.post(
            SILICONFLOW_API_URL, 
            headers=headers, 
            json=payload,
            timeout=30  # 添加超时设置
        )
        response.raise_for_status()
        
        result = response.json()
        logger.info("API请求成功")
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    except requests.exceptions.Timeout:
        logger.error("API请求超时")
        return "请求超时，请稍后重试。"
    except requests.exceptions.RequestException as e:
        logger.error(f"硅基流动API调用失败: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"错误响应: {e.response.text}")
        return "图纸分析失败，请稍后重试。"
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")
        return "处理过程中发生错误，请稍后重试。"

def process_image_with_siliconflow(image_file):
    """处理图片并调用硅基流动API"""
    try:
        # 读取图片并转换为base64
        file_content = image_file.read()
        nparr = np.frombuffer(file_content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 将图片转换为base64
        _, buffer = cv2.imencode('.jpg', img)
        image_base64 = base64.b64encode(buffer).decode()
        
        # 调用硅基流动API
        analysis = analyze_image_with_siliconflow(image_base64)
        
        return {
            "success": True,
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"图片处理失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@main_bp.route('/')
def index():
    """首页路由"""
    logger.info("接收到根路由请求")
    logger.debug(f"模板路径: {os.path.abspath('templates/index.html')}")
    return render_template('index.html', 
                          model_loaded=model_loaded,
                          message="模型正在加载中，请稍候..." if not model_loaded else "",
                          error=model_load_error)

@main_bp.route('/api/detection/model/status', methods=['GET'])
def get_model_status():
    """获取模型状态"""
    try:
        return jsonify(detection_service.get_model_status())
    except Exception as e:
        logger.error(f"获取模型状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 移除重复的/api/detect路由定义，该路由已在detection_bp中定义

def process_image(image_file, model):
    """处理上传的图片并返回检测结果"""
    try:
        # 1. 读取文件内容
        file_content = image_file.read()
        if len(file_content) == 0:
            raise ValueError("上传的文件为空")

        # 2. 将文件内容转换为numpy数组
        nparr = np.frombuffer(file_content, np.uint8)
        original_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if original_img is None:
            raise ValueError("图片解码失败")
            
        logger.info(f"图片读取成功: 形状 {original_img.shape}")

        # 3. 目标检测
        try:
            results = model(original_img)[0]
            
            # 保存原始的类别名称
            original_names = results.names.copy()
            
            # 将英文类别名称替换为中文
            for idx, name in original_names.items():
                if name in CLASS_MAPPING:
                    results.names[idx] = CLASS_MAPPING[name]
            
            # 4. 使用YOLO自带的绘图功能，但不显示置信度
            detected_img = results.plot(
                line_width=3,          # 设置线条粗细
                boxes=True,            # 显示边界框
                labels=True,           # 显示标签
                conf=False             # 不显示置信度
            )
            
            # 5. 统计每个类别的检测结果
            class_counts = {}
            detections = []
            
            for box in results.boxes:
                cls = int(box.cls[0])
                en_class_name = original_names[cls]
                zh_class_name = CLASS_MAPPING.get(en_class_name, en_class_name)
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # 更新类别计数
                if zh_class_name not in class_counts:
                    class_counts[zh_class_name] = 1
                else:
                    class_counts[zh_class_name] += 1
                
                # 保存检测详情
                detections.append({
                    'class': zh_class_name,
                    'confidence': conf,
                    'bbox': [x1, y1, x2, y2]
                })
            
            # 6. 编码原图和检测后的图像
            _, original_buffer = cv2.imencode('.png', original_img)
            _, detected_buffer = cv2.imencode('.png', detected_img)
            
            # 7. 准备返回数据
            response_data = {
                'original_image': base64.b64encode(original_buffer).decode(),
                'detected_image': base64.b64encode(detected_buffer).decode(),
                'class_summary': [
                    {'class': class_name, 'count': count}
                    for class_name, count in class_counts.items()
                ],
                'detections': detections
            }
            
            # 记录检测统计信息
            logger.info("检测结果统计:")
            for class_name, count in class_counts.items():
                logger.info(f"{class_name}: {count}个")
            
            return response_data

        except Exception as e:
            logger.error(f"目标检测失败: {e}")
            raise ValueError(f"目标检测失败: {str(e)}")

    except Exception as e:
        logger.error(f"图片处理失败: {e}")
        raise

@main_bp.route('/api/network_check')
def network_check():
    """网络诊断接口"""
    try:
        # 测试硅基流动API连接
        headers = {
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.get(
            "https://api.siliconflow.com/v1/models",
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        
        return jsonify({
            'success': True,
            'message': '网络连接正常',
            'api_status': '可用'
        }), 200
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'message': '网络连接超时',
            'api_status': '不可用'
        }), 504
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'message': f'网络连接错误: {str(e)}',
            'api_status': '不可用'
        }), 502

@main_bp.route('/api/analyze', methods=['POST'])
def analyze():
    """处理图片分析请求"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有上传文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'})
    
    try:
        result = process_image_with_siliconflow(file)
        return jsonify(result)
    except Exception as e:
        logger.error(f"分析失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

def load_model():
    """加载模型"""
    global model, model_loaded
    try:
        model_path = current_app.config['MODEL_PATH']
        if not os.path.exists(model_path):
            logging.error(f"模型文件不存在: {model_path}")
            return False
        
        model = YOLO(model_path)
        model_loaded = True
        logging.info(f"模型加载成功: {model_path}")
        return True
    except Exception as e:
        logging.error(f"加载模型失败: {str(e)}")
        return False



if __name__ == '__main__':
    # 在后台线程中加载模型
    model_thread = threading.Thread(target=load_model)
    model_thread.daemon = True
    model_thread.start()
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)