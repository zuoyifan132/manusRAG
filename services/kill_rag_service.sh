#!/bin/bash

# 从环境变量获取端口，如果未设置则使用默认值
PORT=${PORT:-17724}

echo "正在关闭端口 $PORT 上的所有服务..."

# 查找监听指定端口的进程
PIDS=$(lsof -i:$PORT -t)

if [ -z "$PIDS" ]; then
    echo "未发现任何进程监听端口 $PORT"
    exit 0
fi

# 杀掉所有找到的进程
echo "发现以下进程正在监听端口 $PORT: $PIDS"
for PID in $PIDS; do
    echo "正在终止进程 $PID"
    kill -9 $PID
done

# 确认进程已被终止
sleep 1
if [ -z "$(lsof -i:$PORT -t)" ]; then
    echo "所有进程已成功终止"
else
    echo "警告: 部分进程可能未成功终止，请手动检查"
fi
