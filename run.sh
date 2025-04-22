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

# 启动 reranker 服务
echo -e "${BLUE}[INFO]${NC} 正在启动 Reranker 服务..."
cd $BASE_DIR/utils/bge_reranker_v2_m3
bash run_reranker.sh
sleep 10

# 检查 reranker 服务是否成功启动
RERANKER_PORT=12212
if lsof -i:$RERANKER_PORT -t &> /dev/null; then
    echo -e "${GREEN}[SUCCESS]${NC} Reranker 服务已成功启动"
else
    echo -e "${RED}[ERROR]${NC} Reranker 服务启动失败"
fi
echo "====================================================="

# 启动 minerU 服务
echo -e "${BLUE}[INFO]${NC} 正在启动 MinerU 服务..."
cd $BASE_DIR/utils/minerU_app
bash run_minerU_app.sh
sleep 10

# 检查 minerU 服务是否成功启动
MINERU_PORT=8888
if lsof -i:$MINERU_PORT -t &> /dev/null; then
    echo -e "${GREEN}[SUCCESS]${NC} MinerU 服务已成功启动"
else
    echo -e "${YELLOW}[WARNING]${NC} MinerU 服务启动失败或未监听端口 $MINERU_PORT"
    echo -e "${YELLOW}[WARNING]${NC} 检查日志文件: $BASE_DIR/utils/minerU_app/minerU_app.log"
    # 即使 minerU 启动失败，我们仍然继续执行后续步骤
fi
echo "====================================================="

# 启动 RAG 服务
echo -e "${BLUE}[INFO]${NC} 正在启动 RAG 服务..."
cd $BASE_DIR/services
bash run_rag_service.sh
sleep 10

# 检查 RAG 服务是否成功启动
RAG_PORT=17724
if lsof -i:$RAG_PORT -t &> /dev/null; then
    echo -e "${GREEN}[SUCCESS]${NC} RAG 服务已成功启动"
else
    echo -e "${RED}[ERROR]${NC} RAG 服务启动失败"
    echo -e "${RED}[ERROR]${NC} 检查日志文件: $BASE_DIR/services/service.log"
fi
echo "====================================================="

# 启动 WebUI
echo -e "${BLUE}[INFO]${NC} 正在启动 WebUI..."
cd $BASE_DIR/webui
echo -e "${GREEN}[LAUNCHING]${NC} 启动 Flash Browser..."
streamlit run flash_broswer.py 