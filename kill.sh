#!/bin/bash

# 设置基本路径
BASE_DIR="$(pwd)"
echo "当前工作目录: $BASE_DIR"
echo "====================================================="

# 设置日志颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 关闭 RAG 服务
echo -e "${BLUE}[INFO]${NC} 正在关闭 RAG 服务..."
cd $BASE_DIR/services
bash kill_rag_service.sh
echo "====================================================="

# 关闭 reranker 服务
echo -e "${BLUE}[INFO]${NC} 正在关闭 Reranker 服务..."
cd $BASE_DIR/utils/bge_reranker_v2_m3
bash kill_reranker.sh
echo "====================================================="

# 关闭 minerU 服务
echo -e "${BLUE}[INFO]${NC} 正在关闭 MinerU 服务..."
cd $BASE_DIR/utils/minerU_app
bash kill_minerU.sh
echo "====================================================="

# 关闭 Streamlit 服务
echo -e "${BLUE}[INFO]${NC} 正在关闭 Streamlit 服务..."
# 查找监听8501端口的进程 (Streamlit默认端口)
STREAMLIT_PIDS=$(lsof -i:8501 -t)

if [ -z "$STREAMLIT_PIDS" ]; then
    echo -e "${YELLOW}[WARNING]${NC} 未发现任何 Streamlit 进程"
else
    echo -e "${GREEN}[SUCCESS]${NC} 发现以下 Streamlit 进程: $STREAMLIT_PIDS"
    for PID in $STREAMLIT_PIDS; do
        echo -e "${BLUE}[INFO]${NC} 正在终止 Streamlit 进程 $PID"
        kill -9 $PID
    done
    
    # 确认进程已被终止
    sleep 1
    if [ -z "$(lsof -i:8501 -t)" ]; then
        echo -e "${GREEN}[SUCCESS]${NC} 所有 Streamlit 进程已成功终止"
    else
        echo -e "${RED}[ERROR]${NC} 警告: 部分 Streamlit 进程可能未成功终止，请手动检查"
    fi
fi

# 查找还在运行的python进程（可能是相关服务）
PYTHON_PIDS=$(ps aux | grep -E "flash_broswer.py|app.py" | grep -v grep | awk '{print $2}')

if [ -n "$PYTHON_PIDS" ]; then
    echo -e "${BLUE}[INFO]${NC} 发现以下可能相关的Python进程: $PYTHON_PIDS"
    for PID in $PYTHON_PIDS; do
        echo -e "${BLUE}[INFO]${NC} 正在终止Python进程 $PID"
        kill -9 $PID
    done
fi

echo "====================================================="
echo -e "${GREEN}[DONE]${NC} 所有服务已尝试关闭，请检查是否有残留进程" 