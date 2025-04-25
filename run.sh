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

# 定义端口监控函数
wait_for_port() {
    local port=$1
    local service_name=$2
    local max_attempts=$3
    local log_file=$4
    
    echo -e "${BLUE}[INFO]${NC} 等待 $service_name 服务在端口 $port 上启动..."
    
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if lsof -i:$port -t &> /dev/null; then
            echo -e "${GREEN}[SUCCESS]${NC} $service_name 服务已成功启动在端口 $port"
            return 0
        fi
        
        echo -e "${YELLOW}[WAITING]${NC} $service_name 服务启动中... (尝试 $attempt/$max_attempts)"
        sleep 3
        ((attempt++))
    done
    
    echo -e "${RED}[ERROR]${NC} $service_name 服务在 $max_attempts 次尝试后仍未启动"
    if [ ! -z "$log_file" ]; then
        echo -e "${RED}[ERROR]${NC} 检查日志文件: $log_file"
    fi
    
    # 返回失败状态但继续执行脚本
    return 1
}

# 启动 reranker 服务
echo -e "${BLUE}[INFO]${NC} 正在启动 Reranker 服务..."
cd $BASE_DIR/utils/bge_reranker_v2_m3
bash run_reranker.sh

# 等待 reranker 服务启动
RERANKER_PORT=12212
wait_for_port $RERANKER_PORT "Reranker" 20 "$BASE_DIR/utils/bge_reranker_v2_m3/reranker_service.log"
echo "====================================================="

# 启动 minerU 服务
echo -e "${BLUE}[INFO]${NC} 正在启动 MinerU 服务..."
cd $BASE_DIR/utils/minerU_app
bash run_minerU_app.sh

# 等待 minerU 服务启动
MINERU_PORT=8888
if ! wait_for_port $MINERU_PORT "MinerU" 20 "$BASE_DIR/utils/minerU_app/minerU_app.log"; then
    echo -e "${YELLOW}[WARNING]${NC} MinerU 服务启动失败或未监听端口 $MINERU_PORT，但将继续执行后续步骤"
fi
echo "====================================================="

# 启动 RAG 服务
echo -e "${BLUE}[INFO]${NC} 正在启动 RAG 服务..."
cd $BASE_DIR/services
bash run_rag_service.sh

# 等待 RAG 服务启动
RAG_PORT=17724
wait_for_port $RAG_PORT "RAG" 20 "$BASE_DIR/services/service.log"
echo "====================================================="

# 启动 WebUI
echo -e "${BLUE}[INFO]${NC} 正在启动 WebUI..."
cd $BASE_DIR/webui
echo -e "${GREEN}[LAUNCHING]${NC} 启动 Flash Browser..."
streamlit run flash_broswer.py 