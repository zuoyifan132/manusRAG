#!/bin/bash

echo "[INFO] Script Starting ..."

# 设置运行配置
ProjectDir="/Users/evan/Desktop/work/wind/FlashC/rag/utils/minerU_app"
# ProjectDir="/mnt/storage/yliu/mineru_app/"

# 切换工作目录
cd ${ProjectDir} && pwd

# 启动App服务
echo "[INFO] App Service Run Starting ..."
export MINERU_TOOLS_CONFIG_JSON="${ProjectDir}/magic-pdf.json"

# python app.py
# nohup python app.py > /dev/null 2>&1 &
nohup python app.py > minerU_app.log 2>&1 &
echo "[INFO] App Service Run Completed."

echo "[INFO] Script Completed."
