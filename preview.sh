#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查并清理已占用的端口
cleanup_ports() {
    echo -e "${BLUE}检查端口占用情况...${NC}"
    for port in 8080; do
        if lsof -i :$port > /dev/null; then
            echo -e "${RED}端口 $port 被占用，正在清理...${NC}"
            lsof -ti :$port | xargs kill -9 2>/dev/null
            sleep 1
        fi
    done
}

# 清理函数
cleanup() {
    echo -e "\n${RED}正在停止前端服务...${NC}"
    # 停止前端服务
    if [ -f .frontend.pid ]; then
        kill $(cat .frontend.pid) 2>/dev/null
        rm .frontend.pid 2>/dev/null
    fi
    
    # 清理端口
    cleanup_ports
    
    echo -e "${GREEN}前端服务已停止${NC}"
    exit 0
}

# 检查服务状态
check_service() {
    local port=$1
    local max_attempts=$2
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$port" >/dev/null; then
            return 0
        fi
        echo -e "${BLUE}等待服务启动 (尝试 $attempt/$max_attempts)...${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done
    return 1
}

# 设置清理钩子
trap cleanup SIGINT SIGTERM

# 清理已占用的端口
cleanup_ports

# 创建日志目录
mkdir -p logs

# 打印启动信息
echo -e "${BLUE}正在启动 YOLOv11 前端预览服务...${NC}"

# 进入前端目录
cd frontend

# 检查并安装依赖
echo -e "${GREEN}检查并安装依赖...${NC}"
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}正在安装依赖包...${NC}"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}依赖安装失败，请检查网络连接或 npm 配置${NC}"
        exit 1
    fi
fi

# 启动前端服务
echo -e "${GREEN}启动前端服务...${NC}"
npm run dev -- --port 8080 --host > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

# 等待前端服务启动
echo -e "${BLUE}等待前端服务启动...${NC}"
if ! check_service 8080 10; then
    echo -e "${RED}前端服务启动失败，请检查 logs/frontend.log${NC}"
    cleanup
    exit 1
fi

# 保存进程ID
echo $FRONTEND_PID > .frontend.pid

# 等待用户输入
echo -e "${BLUE}前端预览服务已启动:${NC}"
echo -e "前端服务运行在: http://localhost:8080"
echo -e "日志文件位置:"
echo -e "  - 前端日志: logs/frontend.log"
echo -e "\n按 Ctrl+C 停止服务"

# 监控服务状态
while true; do
    if ! ps -p $FRONTEND_PID > /dev/null; then
        echo -e "${RED}前端服务已停止，请检查 logs/frontend.log${NC}"
        cleanup
        exit 1
    fi
    sleep 5
done 