# YOLOv11 施工规范检测系统

## 项目简介
这是一个基于YOLOv11的施工规范检测系统，用于自动识别和检测施工现场中的违规行为和安全隐患。系统包含模型训练、目标检测API服务和前端可视化界面三个核心模块。

## 项目架构

```
├── backend/          # 后端服务
│   ├── app/         # API应用
│   ├── config/      # 配置文件
│   └── models/      # 模型文件
├── frontend/        # 前端界面
│   ├── src/         # 源代码
│   └── public/      # 静态资源
└── training/        # 模型训练
    ├── data/        # 训练数据
    └── models/      # 训练模型
```

## 核心功能

### 1. 模型训练模块
- 支持自定义数据集训练
- 提供预训练模型
- 支持模型评估和验证
- 训练过程可视化

### 2. 目标检测API服务
- RESTful API接口
- 实时图像处理
- 违规行为检测
- 结果输出和存储

### 3. 前端可视化界面
- 实时检测展示
- 历史记录查询
- 检测结果统计
- 系统配置管理

## 快速开始

### 环境要求
- Python 3.8+
- Node.js 14+
- CUDA 11.0+（用于GPU训练）

### 安装步骤

1. 克隆项目
```bash
git clone [项目地址]
cd yolov11
```

2. 安装后端依赖
```bash
cd backend
pip install -r requirements.txt
```

3. 安装前端依赖
```bash
cd frontend
npm install
```

### 启动服务

1. 启动后端服务
```bash
cd backend
python run.py
```

2. 启动前端服务
```bash
cd frontend
npm run dev
```

## 使用说明

### 模型训练
1. 准备数据集
2. 修改配置文件
3. 执行训练脚本
4. 评估模型效果

### API调用
- POST /api/detect - 上传图片进行检测
- GET /api/status - 获取系统状态
- GET /api/history - 获取历史记录

### 前端操作
1. 打开浏览器访问系统
2. 上传图片或视频
3. 查看检测结果
4. 管理系统配置

## 开发指南

### 代码规范
- 遵循PEP 8 Python代码规范
- 使用ESLint进行JavaScript代码检查
- 编写清晰的代码注释
- 保持代码简洁可维护

### Git工作流
1. 创建功能分支
2. 提交代码更改
3. 提交Pull Request
4. 代码审查合并

## 注意事项
1. 定期备份重要数据
2. 及时更新依赖包
3. 遵循安全开发规范
4. 保护敏感配置信息

## 贡献指南
欢迎提交Issue和Pull Request来帮助改进项目。

## 许可证
本项目采用MIT许可证。