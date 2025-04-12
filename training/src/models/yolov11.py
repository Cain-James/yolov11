import torch
import torch.nn as nn
import torchvision.models as models
import os

class YOLOv11(nn.Module):
    def __init__(self, num_classes=10, backbone='resnet50', pretrained=False, pretrained_path=None):
        super(YOLOv11, self).__init__()
        # 加载主干网络
        if backbone == 'resnet50':
            backbone_model = models.resnet50(weights=None)  # 不使用torchvision的预训练权重
            self.backbone_channels = 2048
            # 提取特征层
            self.backbone = nn.Sequential(*list(backbone_model.children())[:-2])
        elif backbone == 'mobilenet_v2':
            backbone_model = models.mobilenet_v2(weights=None)  # 不使用torchvision的预训练权重
            self.backbone_channels = 1280
            # 提取特征层
            self.backbone = backbone_model.features
        else:
            raise ValueError(f"不支持的主干网络: {backbone}，目前支持的网络有：resnet50, mobilenet_v2")
        
        # 检测头 - 使用更少的通道数以减少内存使用
        mid_channels = min(512, self.backbone_channels)
        self.detect_head = nn.Sequential(
            nn.Conv2d(self.backbone_channels, mid_channels, 1),
            nn.BatchNorm2d(mid_channels),
            nn.LeakyReLU(0.1),
            
            nn.Conv2d(mid_channels, mid_channels // 2, 3, padding=1),
            nn.BatchNorm2d(mid_channels // 2),
            nn.LeakyReLU(0.1),
            
            nn.Conv2d(mid_channels // 2, (num_classes + 5) * 3, 1)  # 3个anchor boxes
        )

        # 加载本地预训练模型
        if pretrained and pretrained_path and os.path.exists(pretrained_path):
            print(f"加载本地预训练模型: {pretrained_path}")
            try:
                # 使用weights_only=True来安全加载模型
                state_dict = torch.load(pretrained_path, weights_only=True)
                
                # 如果是DetectionModel对象，获取其状态字典
                if hasattr(state_dict, 'state_dict'):
                    state_dict = state_dict.state_dict()
                
                # 提取backbone和detect_head的权重
                backbone_state_dict = {}
                detect_head_state_dict = {}
                
                # 打印模型结构以进行调试
                print("预训练模型结构:")
                for k in state_dict.keys():
                    print(f"  {k}")
                
                # 根据预训练模型的结构提取权重
                for k, v in state_dict.items():
                    # 处理backbone权重
                    if any(k.startswith(prefix) for prefix in ['backbone.', 'model.backbone.', 'features.']):
                        new_key = k.split('.')[-1]  # 只保留最后一层
                        backbone_state_dict[new_key] = v
                    # 处理检测头权重
                    elif any(k.startswith(prefix) for prefix in ['detect_head.', 'model.detect_head.', 'head.']):
                        new_key = k.split('.')[-1]  # 只保留最后一层
                        detect_head_state_dict[new_key] = v
                
                # 加载backbone权重
                if backbone_state_dict:
                    try:
                        self.backbone.load_state_dict(backbone_state_dict)
                        print("Backbone权重加载完成")
                    except Exception as e:
                        print(f"Backbone权重加载失败: {e}")
                
                # 加载detect_head权重
                if detect_head_state_dict:
                    try:
                        self.detect_head.load_state_dict(detect_head_state_dict)
                        print("Detect head权重加载完成")
                    except Exception as e:
                        print(f"Detect head权重加载失败: {e}")
                
            except Exception as e:
                print(f"预训练模型加载失败: {e}")
                print("使用随机初始化权重")
                self._initialize_weights()
        else:
            # 初始化权重
            self._initialize_weights()

        # 确保所有参数都启用梯度计算
        for param in self.parameters():
            param.requires_grad = True

    def forward(self, x):
        # 特征提取
        features = self.backbone(x)
        
        # 检测头
        output = self.detect_head(features)
        
        # 重塑输出
        batch_size, _, height, width = output.shape
        output = output.view(batch_size, 3, height, width, -1)  # [batch_size, num_anchors, height, width, 5 + num_classes]
        
        # 应用sigmoid到置信度和类别预测
        output[..., 4:5] = torch.sigmoid(output[..., 4:5])  # confidence
        output[..., 5:] = torch.sigmoid(output[..., 5:])    # class probabilities
        
        # 应用sigmoid到x, y坐标
        output[..., 0:2] = torch.sigmoid(output[..., 0:2])
        
        # 应用exp到宽高
        output[..., 2:4] = torch.exp(output[..., 2:4])
        
        return output

    def _initialize_weights(self):
        for m in self.detect_head.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0) 