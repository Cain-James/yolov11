import os
import torch
import yaml
import gc
import logging
import time
import argparse
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from torch.utils.data import DataLoader
from torch.optim import Adam
from torch.optim.lr_scheduler import CosineAnnealingLR
from models.yolov11 import YOLOv11
from models.loss import YOLOLoss
from data.dataset import create_dataloader
from torch.amp import autocast, GradScaler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training/models/training.log'),
        logging.StreamHandler()
    ]
)

def setup_logger(log_dir="logs"):
    """设置日志记录器"""
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志文件名（使用时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"comparison_{timestamp}.log")
    
    # 配置日志记录器
    logger = logging.getLogger('ModelComparison')
    logger.setLevel(logging.DEBUG)
    
    # 文件处理器 - 记录所有级别的日志
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # 控制台处理器 - 只显示重要信息
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 设置CUDA内存优化
torch.cuda.empty_cache()
gc.collect()  # 主动触发垃圾回收
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
# 尝试为cuDNN使用确定性算法（可能会降低性能但提高可重复性）
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.deterministic = False

class ModelComparison:
    def __init__(self, config_path="training/config/model_config.yaml"):
        """
        初始化模型比较器
        :param config_path: 配置文件路径
        """
        # 设置日志记录器
        self.logger = setup_logger()
        
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"使用设备: {self.device}")
        
        if torch.cuda.is_available():
            self.logger.debug(f"GPU: {torch.cuda.get_device_name(0)}")
            self.logger.debug(f"总内存: {torch.cuda.get_device_properties(0).total_memory / 1024 / 1024 / 1024:.2f} GB")
            self.logger.debug(f"可用内存: {torch.cuda.memory_reserved(0) / 1024 / 1024 / 1024:.2f} GB")
        
        # 初始化混合精度训练的scaler
        self.scaler = GradScaler(enabled=(self.device.type != 'cpu'))
        
        # 初始化日志间隔
        self.log_interval = self.config['training'].get('log_interval', 10)
        
        # 初始化训练参数
        self.current_epoch = 0
        self.num_epochs = self.config['training']['epochs']
        
        # 设置数据
        self.setup_data()
        
        # 创建保存目录
        self.save_dir = os.path.join(self.config['training']['checkpoint_dir'], 'comparison')
        os.makedirs(self.save_dir, exist_ok=True)
        
        # 初始化性能指标
        self.metrics = {
            'yolov11': {
                'train_loss': [],
                'val_loss': [],
                'inference_time': [],
                'memory_usage': [],
                'mAP': [],
                'precision': [],
                'recall': []
            },
            'yolov11_aspp': {
                'train_loss': [],
                'val_loss': [],
                'inference_time': [],
                'memory_usage': [],
                'mAP': [],
                'precision': [],
                'recall': []
            }
        }

    def setup_data(self):
        """设置数据加载器"""
        # 检查数据路径
        img_dir = os.path.join(self.config['data']['train_path'])
        label_dir = os.path.join(self.config['data']['label_dir'])
        
        self.logger.debug("\n检查数据路径:")
        self.logger.debug(f"图片目录: {img_dir}")
        self.logger.debug(f"标签目录: {label_dir}")
        
        # 检查目录是否存在
        for dir_path in [img_dir, label_dir]:
            if not os.path.exists(dir_path):
                self.logger.error(f"目录不存在: {dir_path}")
                raise FileNotFoundError(f"目录不存在: {dir_path}")
        
        # 获取所有图片文件
        img_files = [f for f in os.listdir(img_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
        total_imgs = len(img_files)
        
        # 计算划分数量
        train_size = int(total_imgs * self.config['data']['train_ratio'])
        val_size = int(total_imgs * self.config['data']['val_ratio'])
        
        # 随机打乱并划分数据集
        np.random.shuffle(img_files)
        train_files = img_files[:train_size]
        val_files = img_files[train_size:train_size + val_size]
        test_files = img_files[train_size + val_size:]
        
        self.logger.info(f"数据集划分: 训练集 {len(train_files)}张, 验证集 {len(val_files)}张, 测试集 {len(test_files)}张")
        
        # 获取配置参数
        num_workers = self.config['training'].get('num_workers', 4)
        batch_size = self.config['training'].get('batch_size', 16)
        
        # 创建数据加载器
        self.train_loader = create_dataloader(
            img_dir,
            label_dir,
            batch_size=batch_size,
            img_size=tuple(self.config['model']['input_size']),
            augment=True,
            num_workers=num_workers,
            num_classes=self.config['model']['num_classes'],
            img_files=train_files
        )
        
        self.val_loader = create_dataloader(
            img_dir,
            label_dir,
            batch_size=batch_size,
            img_size=tuple(self.config['model']['input_size']),
            augment=False,
            num_workers=num_workers,
            num_classes=self.config['model']['num_classes'],
            img_files=val_files
        )
        
        self.test_loader = create_dataloader(
            img_dir,
            label_dir,
            batch_size=batch_size,
            img_size=tuple(self.config['model']['input_size']),
            augment=False,
            num_workers=num_workers,
            num_classes=self.config['model']['num_classes'],
            img_files=test_files
        )
        
        # 检查数据
        self.logger.debug("\n检查数据:")
        imgs, targets = next(iter(self.train_loader))
        self.logger.debug(f"批次图片形状: {imgs.shape}")
        self.logger.debug(f"批次目标形状: {targets.shape}")
        
        # 检查目标值范围（只在有目标时）
        if targets.numel() > 0:
            self.logger.debug(f"目标值范围: [{targets.min():.4f}, {targets.max():.4f}]")
            unique_classes = torch.unique(targets[..., 0]).tolist()
            self.logger.debug(f"类别分布: {unique_classes}")
        else:
            self.logger.warning("警告: 当前批次没有目标")

    def _setup_model(self, use_aspp=False):
        """设置模型"""
        if use_aspp:
            from models.yolov11_aspp import YOLOv11ASPP
            model = YOLOv11ASPP(
                num_classes=self.config['model']['num_classes'],
                backbone=self.config['model']['backbone'],
                pretrained=self.config['model'].get('pretrained', False),
                pretrained_path=self.config['model'].get('pretrained_path', None),
                use_aspp=True
            )
        else:
            from models.yolov11 import YOLOv11
            model = YOLOv11(
                num_classes=self.config['model']['num_classes'],
                backbone=self.config['model']['backbone'],
                pretrained=self.config['model'].get('pretrained', False),
                pretrained_path=self.config['model'].get('pretrained_path', None)
            )
        return model.to(self.device)

    def _setup_dataloader(self, mode='train'):
        """设置数据加载器"""
        from data.dataset import YOLODataset
        dataset = YOLODataset(
            img_dir=self.config['data'][f'{mode}_path'],
            label_dir=self.config['data']['label_dir'],
            img_size=tuple(self.config['model']['input_size']),
            augment=(mode == 'train'),
            num_classes=self.config['model']['num_classes']
        )
        return DataLoader(
            dataset,
            batch_size=self.config['training']['batch_size'],
            shuffle=(mode == 'train'),
            num_workers=self.config['training'].get('num_workers', 4),
            pin_memory=True
        )

    def _train_model(self, use_aspp):
        """训练模型"""
        model = self._setup_model(use_aspp)
        train_loader = self._setup_dataloader('train')
        val_loader = self._setup_dataloader('val')
        
        optimizer = Adam(
            model.parameters(),
            lr=self.config['training']['learning_rate'],
            weight_decay=self.config['training']['weight_decay']
        )
        
        scheduler = CosineAnnealingLR(
            optimizer,
            T_max=self.config['training']['epochs']
        )
        
        for epoch in range(self.config['training']['epochs']):
            # 训练一个epoch
            train_loss = self._train_epoch(model, train_loader, optimizer)
            
            # 验证
            val_loss = self._validate(model, val_loader)
            
            # 更新学习率
            scheduler.step()
            
            # 记录指标
            model_key = 'yolov11_aspp' if use_aspp else 'yolov11'
            self.metrics[model_key]['train_loss'].append(train_loss)
            self.metrics[model_key]['val_loss'].append(val_loss)
            
            self.logger.info(f"Epoch {epoch+1}/{self.config['training']['epochs']} - "
                           f"Train Loss: {train_loss:.4f} - Val Loss: {val_loss:.4f}")
        
        return model

    def _train_epoch(self, model, train_loader, optimizer):
        """训练一个epoch"""
        model.train()
        epoch_loss = 0
        for batch_idx, (images, targets) in enumerate(train_loader):
            images = images.to(self.device)
            targets = [{k: v.to(self.device) for k, v in t.items()} for t in targets]
            
            with autocast():
                loss_dict = model(images, targets)
                loss = sum(loss_dict.values())
            
            optimizer.zero_grad()
            self.scaler.scale(loss).backward()
            self.scaler.step(optimizer)
            self.scaler.update()
            
            epoch_loss += loss.item()
        
        return epoch_loss / len(train_loader)

    def _validate(self, model, val_loader):
        """验证模型"""
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for images, targets in val_loader:
                images = images.to(self.device)
                targets = [{k: v.to(self.device) for k, v in t.items()} for t in targets]
                
                with autocast():
                    loss_dict = model(images, targets)
                    loss = sum(loss_dict.values())
                
                val_loss += loss.item()
        
        return val_loss / len(val_loader)

    def _evaluate_model(self, model, use_aspp):
        """评估模型性能"""
        test_loader = self._setup_dataloader('test')
        model.eval()
        
        all_predictions = []
        all_targets = []
        
        with torch.no_grad():
            for images, targets in test_loader:
                images = images.to(self.device)
                outputs = model(images)
                all_predictions.append(outputs.cpu())
                all_targets.append(targets)
        
        # 计算mAP、精确率和召回率
        mAP, precision, recall = self._calculate_metrics(all_predictions, all_targets)
        
        # 记录指标
        model_key = 'yolov11_aspp' if use_aspp else 'yolov11'
        self.metrics[model_key]['mAP'].append(mAP)
        self.metrics[model_key]['precision'].append(precision)
        self.metrics[model_key]['recall'].append(recall)

    def _calculate_metrics(self, predictions, targets):
        """计算mAP、精确率和召回率"""
        # 实现mAP、精确率和召回率的计算逻辑
        # 这里需要根据你的具体模型和数据集来实现
        # 这里只是一个占位符，实际实现需要根据你的数据集和模型来实现
        return 0.75, 0.80, 0.85  # 临时返回值，实际实现需要根据你的数据集和模型来实现

    def _measure_performance(self, model, use_aspp):
        """测量模型性能指标"""
        model.eval()
        model_key = 'yolov11_aspp' if use_aspp else 'yolov11'
        
        # 测量推理时间
        inference_times = []
        memory_usage = []
        
        with torch.no_grad():
            for _ in range(100):  # 测量100次
                # 创建随机输入
                dummy_input = torch.randn(1, 3, *self.config['model']['input_size']).to(self.device)
                
                # 记录内存使用
                if torch.cuda.is_available():
                    torch.cuda.reset_peak_memory_stats()
                
                # 测量推理时间
                start_time = time.time()
                _ = model(dummy_input)
                end_time = time.time()
                
                # 记录指标
                inference_times.append(end_time - start_time)
                if torch.cuda.is_available():
                    memory_usage.append(torch.cuda.max_memory_allocated())
        
        # 计算平均值
        self.metrics[model_key]['inference_time'].append(np.mean(inference_times))
        self.metrics[model_key]['memory_usage'].append(np.mean(memory_usage) if memory_usage else 0)

    def _generate_comparison_plots(self):
        """生成性能对比图"""
        # 创建图表目录
        plots_dir = os.path.join(self.save_dir, 'plots')
        os.makedirs(plots_dir, exist_ok=True)
        
        # 1. 训练和验证损失对比
        plt.figure(figsize=(10, 6))
        epochs = range(1, len(self.metrics['yolov11']['train_loss']) + 1)
        plt.plot(epochs, self.metrics['yolov11']['train_loss'], label='YOLOv11 Train Loss')
        plt.plot(epochs, self.metrics['yolov11']['val_loss'], label='YOLOv11 Val Loss')
        plt.plot(epochs, self.metrics['yolov11_aspp']['train_loss'], label='YOLOv11+ASPP Train Loss')
        plt.plot(epochs, self.metrics['yolov11_aspp']['val_loss'], label='YOLOv11+ASPP Val Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Training and Validation Loss Comparison')
        plt.legend()
        plt.savefig(os.path.join(plots_dir, 'loss_comparison.png'))
        plt.close()
        
        # 2. 性能指标对比
        metrics = ['mAP', 'precision', 'recall', 'inference_time', 'memory_usage']
        values = {
            'YOLOv11': [np.mean(self.metrics['yolov11'][m]) for m in metrics],
            'YOLOv11+ASPP': [np.mean(self.metrics['yolov11_aspp'][m]) for m in metrics]
        }
        
        x = np.arange(len(metrics))
        width = 0.35
        
        plt.figure(figsize=(12, 6))
        plt.bar(x - width/2, values['YOLOv11'], width, label='YOLOv11')
        plt.bar(x + width/2, values['YOLOv11+ASPP'], width, label='YOLOv11+ASPP')
        plt.xlabel('Metrics')
        plt.ylabel('Value')
        plt.title('Performance Metrics Comparison')
        plt.xticks(x, metrics)
        plt.legend()
        plt.savefig(os.path.join(plots_dir, 'metrics_comparison.png'))
        plt.close()

    def _save_comparison_results(self):
        """保存比较结果"""
        results_path = os.path.join(self.save_dir, 'comparison_results.txt')
        with open(results_path, 'w') as f:
            f.write("模型比较结果:\n")
            f.write('=' * 50 + '\n\n')
            
            for model_name, metrics in self.metrics.items():
                f.write(f'{model_name}:\n')
                f.write('-' * 30 + '\n')
                f.write(f'平均训练损失: {np.mean(metrics["train_loss"]):.4f}\n')
                f.write(f'平均验证损失: {np.mean(metrics["val_loss"]):.4f}\n')
                f.write(f'平均mAP: {np.mean(metrics["mAP"]):.4f}\n')
                f.write(f'平均精确率: {np.mean(metrics["precision"]):.4f}\n')
                f.write(f'平均召回率: {np.mean(metrics["recall"]):.4f}\n')
                f.write(f'平均推理时间: {np.mean(metrics["inference_time"])*1000:.2f}ms\n')
                f.write(f'平均内存使用: {np.mean(metrics["memory_usage"])/1024**2:.2f}MB\n')
                f.write('\n')
        
        self.logger.info(f"比较结果已保存到: {results_path}")

    def compare_models(self):
        """比较两个模型的性能"""
        self.logger.info("开始比较模型性能...")
        
        # 训练和评估标准YOLOv11
        self.logger.info("训练和评估标准YOLOv11...")
        model_standard = self._train_model(use_aspp=False)
        self._evaluate_model(model_standard, use_aspp=False)
        self._measure_performance(model_standard, use_aspp=False)
        
        # 训练和评估YOLOv11+ASPP
        self.logger.info("训练和评估YOLOv11+ASPP...")
        model_aspp = self._train_model(use_aspp=True)
        self._evaluate_model(model_aspp, use_aspp=True)
        self._measure_performance(model_aspp, use_aspp=True)
        
        # 生成比较图表
        self._generate_comparison_plots()
        
        # 保存比较结果
        self._save_comparison_results()
        
        self.logger.info("模型比较完成！")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='training/config/model_config.yaml',
                      help='配置文件路径')
    args = parser.parse_args()
    
    comparison = ModelComparison(args.config)
    comparison.compare_models()

if __name__ == '__main__':
    main() 