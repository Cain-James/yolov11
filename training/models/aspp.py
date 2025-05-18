import torch
import torch.nn as nn
import torch.nn.functional as F

class ASPP(nn.Module):
    """空洞空间金字塔池化模块"""
    def __init__(self, in_channels, out_channels, rates=[1, 6, 12, 18], dropout_rate=0.1):
        super(ASPP, self).__init__()
        
        # 1x1 卷积
        self.conv1 = nn.Conv2d(in_channels, out_channels, 1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        
        # 空洞卷积
        self.conv2 = nn.Conv2d(in_channels, out_channels, 3, padding=rates[0], dilation=rates[0], bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        self.conv3 = nn.Conv2d(in_channels, out_channels, 3, padding=rates[1], dilation=rates[1], bias=False)
        self.bn3 = nn.BatchNorm2d(out_channels)
        
        self.conv4 = nn.Conv2d(in_channels, out_channels, 3, padding=rates[2], dilation=rates[2], bias=False)
        self.bn4 = nn.BatchNorm2d(out_channels)
        
        # 全局平均池化分支
        self.global_avg_pool = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels)
        )
        
        # 输出层
        self.conv_out = nn.Conv2d(out_channels * 5, out_channels, 1, bias=False)
        self.bn_out = nn.BatchNorm2d(out_channels)
        
        self.dropout = nn.Dropout2d(dropout_rate)
        
    def forward(self, x):
        size = x.size()[2:]
        
        # 1x1 卷积分支
        x1 = F.relu(self.bn1(self.conv1(x)))
        
        # 空洞卷积分支
        x2 = F.relu(self.bn2(self.conv2(x)))
        x3 = F.relu(self.bn3(self.conv3(x)))
        x4 = F.relu(self.bn4(self.conv4(x)))
        
        # 全局平均池化分支
        x5 = F.relu(self.global_avg_pool(x))
        x5 = F.interpolate(x5, size=size, mode='bilinear', align_corners=True)
        
        # 拼接所有分支
        x = torch.cat((x1, x2, x3, x4, x5), dim=1)
        
        # 输出层
        x = self.conv_out(x)
        x = self.bn_out(x)
        x = F.relu(x)
        x = self.dropout(x)
        
        return x

class ASPPModule(nn.Module):
    """ASPP模块的包装器，用于YOLOv11"""
    def __init__(self, in_channels, out_channels, rates=[1, 6, 12, 18], dropout_rate=0.1):
        super(ASPPModule, self).__init__()
        self.aspp = ASPP(in_channels, out_channels, rates, dropout_rate)
        
    def forward(self, x):
        return self.aspp(x) 