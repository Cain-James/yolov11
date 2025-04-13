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
            # 直接加载默认模型
            self.load_model()
            
            # 类别映射
            self.CATEGORY_MAPPING = {
                # 垂直运输机械
                '塔吊': {'name': '塔吊', 'category': '垂直运输机械', 'color': '#FF4D4F'},
                
                # 施工机械
                '起重机': {'name': '起重机', 'category': '施工机械', 'color': '#FFA940'},
                '挖掘机': {'name': '挖掘机', 'category': '施工机械', 'color': '#FFA940'},
                '搅拌机': {'name': '搅拌机', 'category': '施工机械', 'color': '#FFA940'},
                
                # 临时设施-生活及办公区
                '宿舍': {'name': '宿舍', 'category': '临时设施-生活及办公区', 'color': '#73D13D'},
                '办公室': {'name': '办公室', 'category': '临时设施-生活及办公区', 'color': '#73D13D'},
                '厕所': {'name': '厕所', 'category': '临时设施-生活及办公区', 'color': '#73D13D'},
                
                # 临时设施-生产加工区
                '钢筋加工厂': {'name': '钢筋加工厂', 'category': '临时设施-生产加工区', 'color': '#40A9FF'},
                
                # 临时设施-辅助设施
                '楼梯': {'name': '楼梯', 'category': '临时设施-辅助设施', 'color': '#9254DE'},
                
                # 基础设施
                '大门': {'name': '大门', 'category': '基础设施', 'color': '#36CFC9'},
                '红线': {'name': '红线', 'category': '基础设施', 'color': '#36CFC9'},
                '道路': {'name': '道路', 'category': '基础设施', 'color': '#36CFC9'}
            }

            # 类别颜色映射 (BGR格式)
            self.CATEGORY_COLORS = {
                '起重机': (255, 0, 0),      # 蓝色
                '宿舍': (0, 255, 0),        # 绿色
                '挖掘机': (0, 0, 255),      # 红色
                '大门': (255, 255, 0),      # 青色
                '搅拌机': (255, 0, 255),    # 粉色
                '办公室': (0, 255, 255),    # 黄色
                '红线': (128, 0, 0),        # 深蓝色
                '道路': (0, 128, 0),        # 深绿色
                '楼梯': (0, 0, 128),        # 深红色
                '钢筋加工厂': (128, 128, 0),# 深青色
                '塔吊': (128, 0, 128),      # 深粉色
                '厕所': (0, 128, 128)       # 深黄色
            }
            
            # 加载中文字体
            #self.font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'fonts', 'SimHei.ttf')
            self.font_path = '/home/bailey/Code/yyh/yolov11/backend/fonts/simsun(1).ttc'
            if not os.path.exists(self.font_path):
                self.logger.warning(f"中文字体文件不存在: {self.font_path}")
            
            # 扫描可用模型
            self.available_models = {}
    

    

    
    def load_model(self):
        """加载默认模型 best.pt"""
        try:
            from backend.config.config import Config
            model_path = os.path.join(Config.MODEL_DIR, 'best.pt')
            
            if not os.path.exists(model_path):
                self.logger.error(f"默认模型不存在: {model_path}")
                return False
                
            self.logger.info("正在加载默认模型: best.pt")
            
            # 使用YOLO类直接加载模型
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.logger.info("默认模型加载成功")
            return True
            
        except Exception as e:
            self.logger.error(f"加载模型失败: {str(e)}")
            return False
    

    
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
        elif self.model is None:
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
            
            # 获取类别信息
            category_info = self.CATEGORY_MAPPING.get(class_name, {'name': class_name, 'category': '其他', 'color': '#666666'})
            category_name = category_info['category']
            display_name = category_info['name']
            color = category_info['color']
            
            # 更新类别统计
            if category_name not in class_counts:
                class_counts[category_name] = {'count': 1, 'items': [display_name]}
            else:
                class_counts[category_name]['count'] += 1
                if display_name not in class_counts[category_name]['items']:
                    class_counts[category_name]['items'].append(display_name)
            
            # 获取颜色
            color = self.CATEGORY_COLORS.get(display_name, (0, 0, 255))
            
            # 在图像上绘制边界框
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 3)
            
            # 绘制中文标签
            label = f"{display_name}"
            # 调整标签位置到框的上方
            label_y = max(int(y1) - 25, 0)  # 确保标签不会超出图像边界
            img = self.draw_chinese_text(img, label, (int(x1), label_y), color)
            
            detection = {
                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                'confidence': float(conf),
                'class': display_name,
                'category': category_name,
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
    


# 创建服务实例
detection_service = DetectionService()

# 导出服务实例
__all__ = ['detection_service']