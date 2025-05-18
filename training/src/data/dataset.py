import os
import torch
import cv2
import numpy as np
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
import albumentations as A
from albumentations.pytorch import ToTensorV2

class YOLODataset(Dataset):
    def __init__(self, img_dir, label_dir, img_size=(640, 640), augment=True, num_classes=12, img_files=None):
        self.img_dir = img_dir
        self.label_dir = label_dir
        self.img_size = img_size
        self.augment = augment
        self.num_classes = num_classes
        
        # 获取所有图片文件
        if img_files is None:
            self.img_files = [f for f in os.listdir(img_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
        else:
            self.img_files = img_files
        
        # 数据增强转换 - 减小变换幅度，使用更安全的参数
        self.transform = A.Compose([
            A.Resize(height=img_size[0], width=img_size[1]),
            A.HorizontalFlip(p=0.3),  # 降低翻转概率
            A.RandomBrightnessContrast(
                brightness_limit=0.1,  # 降低亮度变化范围
                contrast_limit=0.1,    # 降低对比度变化范围
                p=0.2
            ),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2()
        ], bbox_params=A.BboxParams(
            format='yolo',
            label_fields=['class_labels'],
            min_visibility=0.3,  # 确保边界框至少30%可见
            check_each_transform=True  # 检查每次转换后的边界框有效性
        ))
        
        # 基本转换（不包含数据增强）
        self.basic_transform = A.Compose([
            A.Resize(height=img_size[0], width=img_size[1]),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2()
        ], bbox_params=A.BboxParams(
            format='yolo',
            label_fields=['class_labels']
        ))

    def __len__(self):
        return len(self.img_files)

    def __getitem__(self, idx):
        """获取数据集中的一个样本"""
        max_attempts = 10  # 最大重试次数
        current_idx = idx
        
        for attempt in range(max_attempts):
            try:
                # 获取图片路径
                img_path = os.path.join(self.img_dir, self.img_files[current_idx])
                
                # 读取图片
                img = cv2.imread(img_path)
                if img is None:
                    print(f"警告: 无法读取图片 {img_path}，尝试下一张")
                    current_idx = (current_idx + 1) % len(self)
                    continue
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                # 获取标签文件路径
                label_path = os.path.join(self.label_dir, 
                                        os.path.splitext(self.img_files[current_idx])[0] + '.txt')
                
                # 读取标签
                if os.path.exists(label_path) and os.path.getsize(label_path) > 0:
                    try:
                        labels = np.loadtxt(label_path).reshape(-1, 5)
                        if len(labels.shape) == 1:
                            labels = labels.reshape(1, -1)
                            
                        # 确保类别ID是整数且在范围内
                        labels[:, 0] = np.clip(np.floor(labels[:, 0]), 0, self.num_classes - 1)
                        
                        # 确保坐标值在[0,1]范围内，同时保持边界框的有效性
                        boxes = labels[:, 1:].copy()
                        
                        # 处理中心点坐标
                        boxes[:, 0] = np.clip(boxes[:, 0], 0.5 * boxes[:, 2], 1 - 0.5 * boxes[:, 2])  # x_center
                        boxes[:, 1] = np.clip(boxes[:, 1], 0.5 * boxes[:, 3], 1 - 0.5 * boxes[:, 3])  # y_center
                        
                        # 限制宽度和高度，确保不会导致边界框超出图像
                        boxes[:, 2] = np.clip(boxes[:, 2], 0.01, 2 * np.minimum(boxes[:, 0], 1 - boxes[:, 0]))  # width
                        boxes[:, 3] = np.clip(boxes[:, 3], 0.01, 2 * np.minimum(boxes[:, 1], 1 - boxes[:, 1]))  # height
                        
                        # 验证边界框的有效性
                        valid_boxes = []
                        valid_labels = []
                        for box, label in zip(boxes, labels[:, 0]):
                            x_center, y_center, width, height = box
                            if (width > 0 and height > 0 and
                                x_center - width/2 >= 0 and x_center + width/2 <= 1 and
                                y_center - height/2 >= 0 and y_center + height/2 <= 1):
                                valid_boxes.append(box)
                                valid_labels.append(label)
                        
                        if not valid_boxes:  # 如果没有有效的边界框，跳过这张图片
                            raise ValueError("没有有效的边界框")
                        
                        boxes = np.array(valid_boxes)
                        class_labels = np.array(valid_labels)
                        
                    except Exception as e:
                        print(f"警告: 处理标签文件 {label_path} 时出错: {str(e)}，使用空标签")
                        boxes = np.zeros((0, 4))
                        class_labels = np.zeros(0)
                else:
                    boxes = np.zeros((0, 4))
                    class_labels = np.zeros(0)
                
                # 应用转换
                try:
                    if self.augment and len(boxes) > 0:
                        transformed = self.transform(
                            image=img,
                            bboxes=boxes,
                            class_labels=class_labels
                        )
                    else:
                        transformed = self.basic_transform(
                            image=img,
                            bboxes=boxes,
                            class_labels=class_labels
                        )
                    
                    img = transformed['image']
                    boxes = np.array(transformed['bboxes'])
                    class_labels = np.array(transformed['class_labels'])
                    
                    # 再次验证转换后的边界框
                    if len(boxes) > 0:
                        # 确保所有坐标都在[0,1]范围内
                        boxes = np.clip(boxes, 0, 1)
                        
                        # 验证边界框的有效性
                        valid_indices = np.all(boxes > 0, axis=1) & np.all(boxes < 1, axis=1)
                        boxes = boxes[valid_indices]
                        class_labels = class_labels[valid_indices]
                    
                    # 创建目标张量
                    targets = np.zeros((len(boxes), 5))
                    if len(boxes):
                        targets[:, 0] = class_labels
                        targets[:, 1:] = boxes
                    
                    return img, torch.FloatTensor(targets)
                
                except Exception as e:
                    print(f"警告: 转换图片 {img_path} 时出错: {str(e)}，尝试下一张")
                    current_idx = (current_idx + 1) % len(self)
                    continue
                
            except Exception as e:
                print(f"警告: 处理样本时出错: {str(e)}，尝试下一张")
                current_idx = (current_idx + 1) % len(self)
                continue
        
        # 如果所有尝试都失败，返回一个空样本
        print(f"警告: 在{max_attempts}次尝试后仍未找到有效样本，返回空样本")
        dummy_img = np.zeros((self.img_size[0], self.img_size[1], 3))
        transformed = self.basic_transform(image=dummy_img, bboxes=np.zeros((0, 4)), class_labels=np.zeros(0))
        return transformed['image'], torch.zeros((0, 5))

def create_dataloader(img_dir, label_dir, batch_size=16, img_size=(640, 640), 
                     augment=True, num_workers=4, num_classes=12, img_files=None):
    """创建数据加载器"""
    dataset = YOLODataset(
        img_dir=img_dir,
        label_dir=label_dir,
        img_size=img_size,
        augment=augment,
        num_classes=num_classes,
        img_files=img_files
    )
    
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        collate_fn=collate_fn
    )

def collate_fn(batch):
    """自定义批次整理函数"""
    imgs, targets = zip(*batch)
    
    # 过滤掉空的目标
    imgs = [img for img, target in batch if len(target) > 0]
    targets = [target for _, target in batch if len(target) > 0]
    
    if len(imgs) == 0:
        # 返回一个空批次
        return torch.zeros((1, 3, 640, 640)), torch.zeros((1, 0, 5))
    
    # 堆叠图片
    imgs = torch.stack(imgs, 0)
    
    # 处理目标
    # 找到批次中最大的目标数量
    max_boxes = max(len(target) for target in targets)
    
    # 创建一个新的目标张量
    batch_size = len(targets)
    new_targets = torch.zeros((batch_size, max_boxes, 5), dtype=targets[0].dtype, device=targets[0].device)
    
    # 填充目标张量
    for i, target in enumerate(targets):
        if len(target) > 0:
            new_targets[i, :len(target)] = target
    
    return imgs, new_targets 