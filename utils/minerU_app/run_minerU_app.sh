#!/bin/bash
set -ex

PROJECT_DIR="$(pwd)"
echo "当前工作目录: $PROJECT_DIR"

# 启动App服务
echo "[INFO] App Service Run Starting ..."
export MINERU_TOOLS_CONFIG_JSON="${PROJECT_DIR}/magic-pdf.json"

# python app.py
nohup python app.py > minerU_app.log 2>&1 &
echo "[INFO] App Service Run Completed."

echo "[INFO] Script Completed."
