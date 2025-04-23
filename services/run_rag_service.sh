#!/bin/bash

# 从环境变量获取配置，如果未设置则使用默认值
PORT=${PORT:-17724}
WORKERS=${WORKERS:-1}
LOG_FILE=${LOG_FILE:-service.log}

echo "正在启动服务..."
echo "端口: $PORT"
echo "工作进程数: $WORKERS"
echo "日志文件: $LOG_FILE"

# 启动服务
# nohup uvicorn app:app --host 0.0.0.0 --port $PORT --workers $WORKERS > $LOG_FILE 2>&1 &
nohup python -m uvicorn app:app --host 0.0.0.0 --port $PORT --workers $WORKERS > $LOG_FILE 2>&1 &

# 显示启动结果
echo "服务已在后台启动，PID: $!"
echo "可通过 'tail -f $LOG_FILE' 查看日志"
