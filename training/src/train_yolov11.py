import os
import torch
import yaml
import gc
import logging
from datetime import datetime
from pathlib import Path
from torch.utils.data import DataLoader
from torch.optim import Adam
from torch.optim.lr_scheduler import CosineAnnealingLR
from models.yolov11 import YOLOv11
from models.loss import YOLOLoss
from data.dataset import create_dataloader
from torch.amp import autocast, GradScaler

def setup_logger(log_dir="logs"):
    """设置日志记录器"""
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志文件名（使用时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"training_{timestamp}.log")
    
    # 配置日志记录器
    logger = logging.getLogger('YOLOv11')
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

# 打印GPU信息
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"总内存: {torch.cuda.get_device_properties(0).total_memory / 1024 / 1024 / 1024:.2f} GB")
    print(f"可用内存: {torch.cuda.memory_reserved(0) / 1024 / 1024 / 1024:.2f} GB")

class YOLOv11Trainer:
    def __init__(self, config_path="training/config/model_config.yaml"):
        """
        初始化训练器
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
        
        # 初始化最佳验证损失
        self.best_val_loss = float('inf')
        
        # 初始化混合精度训练的scaler
        self.scaler = GradScaler(enabled=(self.device.type != 'cpu'))
        
        # 初始化日志间隔
        self.log_interval = self.config['training'].get('log_interval', 10)
        
        # 初始化训练参数
        self.current_epoch = 0
        self.num_epochs = self.config['training']['epochs']
        
        self.setup_model()
        self.setup_data()
        self.setup_training()

    def setup_model(self):
        """设置模型"""
        # 确保空闲内存
        torch.cuda.empty_cache()
        gc.collect()
        
        # 如果模型很大，可以尝试使用fp16或者bf16初始化
        backend = 'fbgemm' if torch.cuda.is_available() else 'qnnpack'
        torch.backends.quantized.engine = backend
        
        # 获取预训练设置
        pretrained = self.config['model'].get('pretrained', False)
        pretrained_path = self.config['model'].get('pretrained_path', None)
        self.logger.debug(f"使用预训练权重: {pretrained}")
        if pretrained_path:
            self.logger.debug(f"预训练模型路径: {pretrained_path}")
        
        self.model = YOLOv11(
            num_classes=self.config['model']['num_classes'],
            backbone=self.config['model']['backbone'],
            pretrained=pretrained,
            pretrained_path=pretrained_path
        ).to(self.device, dtype=torch.float32)  # 显式指定数据类型
        
        # 初始化损失函数
        self.criterion = YOLOLoss(
            num_classes=self.config['model']['num_classes'],
            anchors=self.config['model']['anchors']
        ).to(self.device)
        
        self.logger.info("模型初始化完成")
        
        # 打印模型参数数量
        num_params = sum(p.numel() for p in self.model.parameters())
        self.logger.debug(f"模型参数数量: {num_params/1e6:.2f}M")

    def setup_data(self):
        """设置数据加载器"""
        # 检查数据路径
        train_img_dir = os.path.join(self.config['data']['train_path'])
        train_label_dir = os.path.join('training/data/labels')  # 直接使用标签目录
        val_img_dir = os.path.join(self.config['data']['val_path'])
        val_label_dir = os.path.join('training/data/labels')  # 直接使用标签目录
        
        self.logger.debug("\n检查数据路径:")
        self.logger.debug(f"训练图片目录: {train_img_dir}")
        self.logger.debug(f"训练标签目录: {train_label_dir}")
        self.logger.debug(f"验证图片目录: {val_img_dir}")
        self.logger.debug(f"验证标签目录: {val_label_dir}")
        
        # 检查目录是否存在
        for dir_path in [train_img_dir, train_label_dir, val_img_dir, val_label_dir]:
            if not os.path.exists(dir_path):
                self.logger.error(f"目录不存在: {dir_path}")
                raise FileNotFoundError(f"目录不存在: {dir_path}")
        
        # 获取配置参数，使用默认值
        num_workers = self.config['training'].get('num_workers', 4)  # 默认使用4个工作进程
        batch_size = self.config['training'].get('batch_size', 16)  # 默认批次大小为16
        
        # 创建数据加载器
        self.train_loader = create_dataloader(
            train_img_dir,
            train_label_dir,
            batch_size=batch_size,
            img_size=tuple(self.config['model']['input_size']),
            augment=True,
            num_workers=num_workers,
            num_classes=self.config['model']['num_classes']
        )
        
        self.val_loader = create_dataloader(
            val_img_dir,
            val_label_dir,
            batch_size=batch_size,
            img_size=tuple(self.config['model']['input_size']),
            augment=False,
            num_workers=num_workers,
            num_classes=self.config['model']['num_classes']
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

    def setup_training(self):
        """设置训练参数"""
        self.optimizer = Adam(
            self.model.parameters(),
            lr=self.config['training']['learning_rate'],
            weight_decay=self.config['training']['weight_decay']
        )
        
        self.scheduler = CosineAnnealingLR(
            self.optimizer,
            T_max=self.config['training']['epochs'],
            eta_min=self.config['training']['learning_rate'] * 0.01
        )
        
        # 创建检查点目录
        os.makedirs(self.config['training']['checkpoint_dir'], exist_ok=True)
        self.logger.info("训练参数设置完成")

    def train_epoch(self, epoch):
        self.model.train()
        total_loss = 0
        num_batches = len(self.train_loader)
        
        # 创建保存目录
        save_dir = os.path.join(self.config['training']['checkpoint_dir'], f'epoch_{epoch}')
        os.makedirs(save_dir, exist_ok=True)
        
        for batch_idx, (imgs, targets) in enumerate(self.train_loader):
            imgs = imgs.to(self.device)
            targets = targets.to(self.device)
            
            # 检查目标值范围
            if targets.max() > 1.0:
                print(f"警告: 目标值超出范围: {targets.min().item():.4f}, {targets.max().item():.4f}")
                targets = torch.clamp(targets, 0, 1)
            
            # 前向传播
            outputs = self.model(imgs)
            
            # 计算损失
            loss, loss_components = self.criterion(outputs, targets)
            
            # 检查损失值
            if torch.isnan(loss):
                print(f"警告: 损失值为NaN，跳过此批次")
                continue
                
            # 反向传播
            self.optimizer.zero_grad()
            loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=10.0)
            
            self.optimizer.step()
            
            # 更新学习率
            self.scheduler.step()
            
            total_loss += loss.item()
            
            # 记录损失组件
            if batch_idx % self.log_interval == 0:
                self.logger.debug(f"Loss Components: {loss_components}")
            
            # 保存中间模型
            if batch_idx % 10 == 0:
                model_path = os.path.join(save_dir, f'model_batch_{batch_idx}.pth')
                torch.save({
                    'epoch': epoch,
                    'batch': batch_idx,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'loss': loss.item(),
                    'loss_components': {k: v.item() for k, v in loss_components.items()}
                }, model_path)
        
        # 计算平均损失
        avg_loss = total_loss / num_batches
        return avg_loss

    def validate(self, epoch):
        """验证模型性能"""
        self.model.eval()
        total_loss = 0
        num_batches = len(self.val_loader)
        
        with torch.no_grad():
            for batch_idx, (imgs, targets) in enumerate(self.val_loader):
                imgs = imgs.to(self.device)
                targets = targets.to(self.device)
                
                # 前向传播
                outputs = self.model(imgs)
                
                # 计算损失
                loss, loss_components = self.criterion(outputs, targets)
                
                # 检查损失值
                if torch.isnan(loss):
                    self.logger.warning(f"验证批次 {batch_idx} 损失为NaN，跳过此批次")
                    continue
                
                total_loss += loss.item()
                
                # 记录损失组件
                if batch_idx % self.log_interval == 0:
                    self.logger.debug(f"验证批次损失: {loss.item():.4f}, 损失组件: {loss_components}")
        
        # 计算平均损失
        avg_loss = total_loss / num_batches if num_batches > 0 else float('inf')
        
        # 检查平均损失
        if torch.isnan(torch.tensor(avg_loss)):
            self.logger.warning("验证平均损失为NaN，使用无穷大")
            avg_loss = float('inf')
        
        return avg_loss

    def save_checkpoint(self, epoch, val_loss):
        """保存检查点"""
        # 保存最新检查点
        latest_path = os.path.join(self.config['training']['checkpoint_dir'], 'latest.pt')
        torch.save(self.model.state_dict(), latest_path)
        
        # 如果是最佳模型，保存为best_model.pt
        if val_loss < self.best_val_loss:
            self.best_val_loss = val_loss
            best_path = os.path.join(self.config['training']['checkpoint_dir'], 'best_model.pt')
            # 直接保存模型状态字典，不包含其他信息
            torch.save(self.model.state_dict(), best_path)
            self.logger.info(f"保存最佳模型到: {best_path}")
            
            # 同时保存一个用于后端的模型
            backend_path = os.path.join(self.config['training']['checkpoint_dir'], 'backend_model.pt')
            # 将模型转换为推理模式
            self.model.eval()
            # 保存完整的模型（包含模型结构）
            torch.save(self.model, backend_path)
            self.logger.debug(f"保存后端模型到: {backend_path}")

    def train(self):
        """开始训练"""
        self.logger.info("开始训练...")
        best_loss = float('inf')
        best_model_path = None
        
        for epoch in range(self.num_epochs):
            self.logger.info(f"\nEpoch {epoch}/{self.num_epochs}")
            
            # 训练一个epoch
            train_loss = self.train_epoch(epoch)
            
            # 验证
            val_loss = self.validate(epoch)
            
            # 记录训练信息
            self.logger.info(f"Epoch [{epoch}/{self.num_epochs}] Train Loss: {train_loss:.4f} Val Loss: {val_loss:.4f}")
            
            # 保存最佳模型
            if val_loss < best_loss:
                best_loss = val_loss
                best_model_path = os.path.join(self.config['training']['checkpoint_dir'], f'best_model_epoch_{epoch}.pth')
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'train_loss': train_loss,
                    'val_loss': val_loss
                }, best_model_path)
                self.logger.info(f"保存最佳模型到: {best_model_path}")
            
            # 保存最后一个epoch的模型
            if epoch == self.num_epochs - 1:
                last_model_path = os.path.join(self.config['training']['checkpoint_dir'], f'last_model_epoch_{epoch}.pth')
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'train_loss': train_loss,
                    'val_loss': val_loss
                }, last_model_path)
                self.logger.info(f"保存最后一个模型到: {last_model_path}")

if __name__ == "__main__":
    trainer = YOLOv11Trainer()
    trainer.train() 