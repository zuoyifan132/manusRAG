import os
import json
import hashlib
import time
import threading
from pathlib import Path
from datetime import datetime
from loguru import logger
from core import flash_rag

# 尝试导入schedule包，如果不存在则自动安装
try:
    import schedule
except ImportError:
    import subprocess
    import sys
    logger.info("正在安装schedule包...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "schedule"])
    import schedule

# 创建 webui/data 目录
WEBUI_PATH = Path(__file__).absolute().parent.parent
DATA_DIR = os.path.join(WEBUI_PATH, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# MD5文件存储路径
MD5_FILE_PATH = os.path.join(DATA_DIR, "file_MD5.json")

def calculate_md5(file_path):
    """计算文件的MD5值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"计算文件 {file_path} MD5值失败: {str(e)}")
        return None

def get_all_files(directory):
    """递归获取目录下所有文件的路径"""
    all_files = []
    try:
        for root, _, files in os.walk(directory):
            for file in files:
                # 忽略隐藏文件
                if not file.startswith('.'):
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)
    except Exception as e:
        logger.error(f"遍历目录 {directory} 失败: {str(e)}")
    return all_files

def load_md5_data():
    """加载保存的MD5数据"""
    if os.path.exists(MD5_FILE_PATH):
        try:
            with open(MD5_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载MD5数据文件失败: {str(e)}")
            return {}
    else:
        return {}

def save_md5_data(md5_data):
    """保存MD5数据到文件"""
    try:
        with open(MD5_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(md5_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存MD5数据文件失败: {str(e)}")
        return False

def scan_directory(directory, config_path):
    """扫描目录并处理文件"""
    if not os.path.exists(directory):
        logger.error(f"监控目录 {directory} 不存在")
        return False
    
    # 获取已保存的MD5数据
    md5_data = load_md5_data()
    
    # 获取当前目录下所有文件
    current_files = get_all_files(directory)
    
    # 跟踪新的MD5数据和需要处理的文件
    new_md5_data = {}
    files_to_process = []
    
    for file_path in current_files:
        # 计算当前文件的MD5值
        current_md5 = calculate_md5(file_path)
        if current_md5:
            # 检查文件是否存在于之前的MD5数据中或MD5值是否变化
            if file_path not in md5_data or md5_data[file_path] != current_md5:
                files_to_process.append(file_path)
            # 更新新的MD5数据
            new_md5_data[file_path] = current_md5
    
    # 处理需要更新的文件
    success_count = 0
    for file_path in files_to_process:
        try:
            logger.info(f"处理文件: {file_path}")
            result = flash_rag.ingest_data(file_path=file_path, config=config_path)
            if result.get("status") == "success":
                success_count += 1
                logger.info(f"成功处理文件: {file_path}")
            else:
                logger.error(f"处理文件失败: {file_path}, 原因: {result.get('message', '未知错误')}")
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时出错: {str(e)}")
    
    # 只有在所有文件都成功处理后才更新MD5数据
    if files_to_process and success_count == len(files_to_process):
        logger.info(f"成功处理了 {success_count} 个文件，正在更新MD5数据")
        save_md5_data(new_md5_data)
        return True
    elif not files_to_process:
        logger.info("没有需要处理的文件")
        return True
    else:
        logger.warning(f"部分文件处理失败，已处理 {success_count}/{len(files_to_process)}")
        return False

class FileMonitor:
    def __init__(self):
        self.monitor_thread = None
        self.running = False
        self.monitor_directory = None
        self.config_path = None
    
    def start(self, directory, config_path):
        """启动文件监控服务"""
        if self.running:
            logger.warning("文件监控服务已在运行中")
            return False
        
        self.monitor_directory = directory
        self.config_path = config_path
        self.running = True
        
        # 立即执行一次扫描
        logger.info(f"启动文件监控服务，监控目录: {directory}")
        scan_directory(directory, config_path)
        
        # 设置每天凌晨12点执行
        schedule.every().day.at("00:00").do(
            lambda: scan_directory(self.monitor_directory, self.config_path)
        )
        
        # 在单独的线程中运行调度任务
        self.monitor_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.monitor_thread.start()
        
        return True
    
    def stop(self):
        """停止文件监控服务"""
        if not self.running:
            return False
        
        self.running = False
        schedule.clear()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            # 等待线程结束
            self.monitor_thread.join(timeout=1)
        
        logger.info("文件监控服务已停止")
        return True
    
    def _run_scheduler(self):
        """运行调度器"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def status(self):
        """获取监控服务状态"""
        if not self.running:
            return {"status": "stopped"}
        
        return {
            "status": "running",
            "directory": self.monitor_directory,
            "config": self.config_path,
            "next_run": schedule.next_run()
        }

# 创建全局文件监控实例
file_monitor = FileMonitor() 