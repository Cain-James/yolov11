import os
import cv2
import numpy as np
import torch
import logging
from threading import Lock
from datetime import datetime
import glob
import base64

class DetectionService:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DetectionService, cls).__new__(cls)
                    cls._instance.model = None
                    cls._instance.current_model_path = None
                    cls._instance.available_models = {}
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.logger = logging.getLogger(__name__)
            self.model = None
            self.current_model_path = None
            self.model_loaded = False
            
            # 类别映射
            self.CATEGORY_MAPPING = {
                'Tower_Crane': '塔吊',
                'Excavator': '挖掘机',
                'Truck': '卡车',
                'Loader': '装载机',
                'Bulldozer': '推土机',
                'Roller': '压路机',
                'Crane': '起重机',
                'Gate': '大门'
            }
            
            # 类别颜色映射 (BGR格式)
            self.CATEGORY_COLORS = {
                '塔吊': (255, 0, 0),      # 蓝色
                '挖掘机': (0, 255, 0),    # 绿色
                '卡车': (0, 0, 255),      # 红色
                '装载机': (255, 255, 0),  # 青色
                '推土机': (255, 0, 255),  # 粉色
                '压路机': (0, 255, 255),  # 黄色
                '起重机': (128, 0, 0),    # 深蓝色
                '大门': (0, 128, 0)       # 深绿色
            }
            
            # 加载中文字体
            #self.font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'fonts', 'SimHei.ttf')
            self.font_path = '/home/bailey/Code/yyh/yolov11/backend/fonts/simsun(1).ttc'
            if not os.path.exists(self.font_path):
                self.logger.warning(f"中文字体文件不存在: {self.font_path}")
            
            # 扫描可用模型
            self.scan_available_models()
    
    def switch_model(self, model_path):
        """切换模型
        Args:
            model_path: 模型文件路径
        Returns:
            bool: 是否切换成功
        """
        try:
            # 检查模型文件是否存在
            if not os.path.exists(model_path):
                self.logger.error(f"模型文件不存在: {model_path}")
                return False
            
            # 如果已经加载了相同的模型，直接返回成功
            if self.model is not None and self.current_model_path == model_path:
                self.logger.info(f"模型 {model_path} 已加载")
                return True
            
            # 关闭当前模型
            if self.model is not None:
                try:
                    # 尝试清理模型
                    del self.model
                    self.model = None
                    self.current_model_path = None
                    self.model_loaded = False
                    import gc
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()  # 清理GPU缓存
                except Exception as e:
                    self.logger.warning(f"清理旧模型时出错: {str(e)}")
            
            # 加载新模型
            try:
                from ultralytics import YOLO
                self.model = YOLO(model_path)
                
                # 验证模型是否加载成功
                if self.model is None:
                    raise Exception("模型加载失败，返回None")
                
                # 验证模型属性
                if not hasattr(self.model, 'names'):
                    raise Exception("模型缺少必要的属性")
                
                # 设置模型状态
                self.current_model_path = model_path
                self.model_loaded = True
                self.logger.info(f"已切换到模型: {model_path}")
                return True
                
            except Exception as e:
                self.logger.error(f"加载新模型失败: {str(e)}")
                self.model = None
                self.current_model_path = None
                self.model_loaded = False
                return False
            
        except Exception as e:
            self.logger.error(f"切换模型失败: {str(e)}")
            return False
    
    def scan_available_models(self):
        """扫描可用的模型文件"""
        try:
            # 使用Config中配置的模型目录
            from backend.config.config import Config
            models_dir = Config.MODEL_DIR
            
            self.logger.info(f"正在扫描模型目录: {models_dir}")
            
            if not os.path.exists(models_dir):
                self.logger.error(f"模型目录不存在: {models_dir}")
                return {}
            
            # 扫描所有.pt文件
            model_files = glob.glob(os.path.join(models_dir, '*.pt'))
            self.available_models = {}
            
            for model_path in model_files:
                model_name = os.path.basename(model_path)
                self.available_models[model_name] = {
                    'path': model_path,
                    'name': model_name,
                    'size': f"{os.path.getsize(model_path) / (1024*1024):.2f}MB",
                    'last_modified': datetime.fromtimestamp(os.path.getmtime(model_path)).strftime('%Y-%m-%d %H:%M:%S')
                }
            
            self.logger.info(f"找到 {len(self.available_models)} 个模型文件")
            for model_name, info in self.available_models.items():
                self.logger.info(f"模型: {model_name}, 大小: {info['size']}, 修改时间: {info['last_modified']}")
            
            return self.available_models
        except Exception as e:
            self.logger.error(f"扫描模型文件失败: {str(e)}")
            return {}
    
    def load_model(self, model_name=None):
        """加载指定的模型
        Args:
            model_name: 模型文件名（如 'best.pt'）
        """
        try:
            # 如果没有指定模型名称，使用默认模型
            if model_name is None:
                model_name = 'best.pt'
            
            # 重新扫描可用模型
            self.scan_available_models()
            
            # 检查模型是否存在
            if model_name not in self.available_models:
                self.logger.error(f"模型 {model_name} 不存在")
                self.model_loaded = False
                return False
            
            model_path = self.available_models[model_name]['path']
            
            # 如果已经加载了相同的模型，直接返回
            if self.model is not None and self.current_model_path == model_path:
                self.logger.info(f"模型 {model_name} 已加载")
                self.model_loaded = True
                return True
            
            self.logger.info(f"正在加载模型: {model_name}")
            self.model_loaded = False
            
            # 使用YOLO类直接加载模型
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.current_model_path = model_path
            self.model_loaded = True
            self.logger.info(f"模型 {model_name} 加载成功")
            return True
            
        except Exception as e:
            self.logger.error(f"加载模型失败: {str(e)}")
            return False
    
    def get_available_models(self):
        """获取所有可用的模型列表"""
        return self.scan_available_models()
    
    def draw_chinese_text(self, img, text, pos, color):
        """在图像上绘制中文文本"""
        # try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        
        # 将OpenCV图像转换为PIL图像
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        # 加载字体
        font = ImageFont.truetype(self.font_path, 200)
        
        # 绘制文本
        draw.text(pos, text, font=font, fill=color)
        
        # 将PIL图像转换回OpenCV图像
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        # except Exception as e:
        #     self.logger.error(f"绘制中文文本失败: {str(e)}")
        #     return img
    
    def process_image(self, image_path, model_path=None):
        """处理图像
        Args:
            image_path: 图像文件路径
            model_path: 可选的模型路径，如果不指定则使用当前加载的模型
        """
        # try:
        # 如果指定了模型路径，尝试加载该模型
        if model_path:
            model_name = os.path.basename(model_path)
            if not self.load_model(model_name):
                raise Exception(f"无法加载指定模型: {model_name}")
        elif not self.model_loaded:
            raise Exception("模型未准备就绪")
        
        # 检查图像文件是否存在
        if not os.path.exists(image_path):
            raise Exception(f"图像文件不存在: {image_path}")
        
        # 读取图像
        img = cv2.imread(image_path)
        if img is None:
            raise Exception("无法读取图像")
        
        # 执行检测
        try:
            results = self.model.predict(img, conf=0.25)[0]  # 设置置信度阈值
        except Exception as e:
            raise Exception(f"模型预测失败: {str(e)}")
        
        # 处理检测结果
        detections = []
        class_counts = {}
        
        # 从结果中获取检测框
        boxes = results.boxes
        for box in boxes:
            #try:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = box.conf[0].item()
            cls = box.cls[0].item()
            class_name = results.names[int(cls)]
            
            # 获取中文类别名
            category = self.CATEGORY_MAPPING.get(class_name, class_name)
            
            # 更新类别计数
            class_counts[category] = class_counts.get(category, 0) + 1
            
            # 获取颜色
            color = self.CATEGORY_COLORS.get(category, (0, 0, 255))
            
            # 在图像上绘制边界框
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 3)
            
            # 绘制中文标签
            label = f"{category} {conf*100:.1f}%"
            # 调整标签位置到框的上方
            label_y = max(int(y1) - 25, 0)  # 确保标签不会超出图像边界
            img = self.draw_chinese_text(img, label, (int(x1), label_y), color)
            
            detection = {
                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                'confidence': float(conf),
                'category': category,
                'color': color
            }
            detections.append(detection)
            # except Exception as e:
            #     self.logger.warning(f"处理单个检测框时出错: {str(e)}")
            #     continue
        
        # 将检测后的图像编码为base64
        try:
            _, buffer = cv2.imencode('.png', img)
            detected_image = base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            self.logger.error(f"图像编码失败: {str(e)}")
            detected_image = None
        
        self.logger.info(f"检测到 {len(detections)} 个目标")
        self.logger.info(f"类别统计: {class_counts}")
        
        return {
            'success': True,
            'data': {
                'detections': detections,
                'class_counts': class_counts,
                'detected_image': detected_image,
                'message': '检测成功'
            }
        }
            
        # except Exception as e:
        #     self.logger.error(f"处理图像失败: {str(e)}")
        #     return {
        #         'success': False,
        #         'data': {
        #             'detections': [],
        #             'class_counts': {},
        #             'detected_image': None,
        #             'message': f"处理图像失败: {str(e)}"
        #         }
        #     }
    
    def get_model_status(self):
        """获取模型状态信息"""
        try:
            # 重新扫描可用模型
            self.scan_available_models()
            
            return {
                'success': True,
                'status': {
                    'available_models': self.available_models,
                    'current_model': self.current_model_path,
                    'loaded': self.model is not None,
                    'total_models': len(self.available_models)
                }
            }
        except Exception as e:
            self.logger.error(f"获取模型状态失败: {str(e)}")
            return {
                'success': False,
                'error': f"获取模型状态失败: {str(e)}"
            }

# 创建服务实例
detection_service = DetectionService()

# 导出服务实例
__all__ = ['detection_service']