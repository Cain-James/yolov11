#!/bin/bash

# 输出系统环境变量
echo "=== 系统环境变量 ==="
env
echo ""

# 输出 CPU 型号
echo "=== CPU 型号 ==="
if command -v lscpu &> /dev/null; then
    lscpu | grep "Model name"
else
    cat /proc/cpuinfo | grep "model name" | uniq
fi
echo ""

# 输出 GPU 型号
echo "=== GPU 型号 ==="
if command -v lspci &> /dev/null; then
    lspci | grep -i vga
fi
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU 信息："
    nvidia-smi
fi
echo ""

# 输出 Python 版本
echo "=== Python 版本 ==="
python3 --version
echo ""

# 输出 PyTorch 版本
echo "=== PyTorch 版本 ==="
if python3 -c "import torch" &> /dev/null; then
    python3 -c "import torch; print('PyTorch Version:', torch.__version__)"
    python3 -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('CUDA Version:', torch.version.cuda)"
else
    echo "PyTorch 未安装"
fi
echo ""

# 输出 CUDA 版本
echo "=== CUDA 版本 ==="
if command -v nvcc &> /dev/null; then
    nvcc --version | grep "release"
else
    echo "nvcc 未安装，无法直接获取 CUDA 版本"
fi