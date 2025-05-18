import torch
import torch.nn as nn
import torch.nn.functional as F

class ASPP(nn.Module):
    """
    Atrous Spatial Pyramid Pooling (ASPP) 模块
    用于捕获多尺度上下文信息
    """
    def __init__(self, in_channels, out_channels, rates=[1, 6, 12, 18]):
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
        
        self.relu = nn.ReLU(inplace=True)
        
    def forward(self, x):
        # 1x1 卷积
        x1 = self.relu(self.bn1(self.conv1(x)))
        
        # 空洞卷积
        x2 = self.relu(self.bn2(self.conv2(x)))
        x3 = self.relu(self.bn3(self.conv3(x)))
        x4 = self.relu(self.bn4(self.conv4(x)))
        
        # 全局平均池化
        x5 = self.global_avg_pool(x)
        x5 = F.interpolate(x5, size=x4.size()[2:], mode='bilinear', align_corners=True)
        
        # 拼接所有分支
        x = torch.cat((x1, x2, x3, x4, x5), dim=1)
        
        # 输出层
        x = self.relu(self.bn_out(self.conv_out(x)))
        
        return x 