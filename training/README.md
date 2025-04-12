# YOLOv11 训练模块

本模块包含了 YOLOv11 模型的训练相关代码和工具。

## 目录结构

```
training/
├── config/             # 配置文件目录
│   └── model_config.yaml  # 模型配置文件
├── data/               # 数据集目录
│   ├── images/        # 图片文件
│   └── labels/        # 标签文件
├── models/            # 模型目录
│   └── checkpoints/   # 检查点保存目录
├── src/               # 源代码目录
│   ├── train_yolov11.py  # 训练主程序
│   └── utils/        # 工具函数
│       ├── organize_dataset.py  # 数据集组织工具
│       ├── sol_empty_txt.py    # 空标签文件处理工具
│       └── split.py           # 数据集分割工具
└── scripts/           # 脚本目录
```

## 使用方法

1. 数据准备
   ```bash
   # 整理数据集
   python src/utils/organize_dataset.py
   
   # 处理空标签文件
   python src/utils/sol_empty_txt.py
   
   # 分割数据集
   python src/utils/split.py
   ```

2. 配置模型
   - 修改 `config/model_config.yaml` 文件，设置模型参数和训练参数

3. 开始训练
   ```bash
   python src/train_yolov11.py
   ```

## 配置说明

### 模型配置
- name: 模型名称
- backbone: 主干网络
- num_classes: 类别数量
- input_size: 输入图片尺寸
- anchors: 锚框设置

### 训练配置
- batch_size: 批次大小
- epochs: 训练轮数
- learning_rate: 学习率
- weight_decay: 权重衰减
- warmup_epochs: 预热轮数
- save_interval: 保存间隔
- eval_interval: 评估间隔

### 数据配置
- train_path: 训练集路径
- val_path: 验证集路径
- test_path: 测试集路径
- num_workers: 数据加载线程数 