"""
配置文件
"""
from pathlib import Path

# 获取当前工作目录
CURRENT_DIR = Path(__file__).parent

# Milvus配置
MILVUS_HOST = "10.106.51.224"  # Milvus服务器地址
MILVUS_PORT = 19530      # Milvus服务器端口
MILVUS_URI = f"http://{MILVUS_HOST}:{MILVUS_PORT}"  # Milvus连接URI
LOCAL_MILVUS_LITE_DB_PATH = f"{CURRENT_DIR}/milvus_db/milvus_db.db"

# Milvus操作重试配置
MILVUS_RETRY_WAIT_TIME = 1  # 重试等待时间（秒）
MILVUS_RETRY_TIMES = 3      # 最大重试次数

# 嵌入API配置
# EMBEDDING_API_URL = "http://10.200.64.10/10-bge-m3/embedding"
EMBEDDING_API_URL = "http://10.100.167.66:13456/bge_m3_embedding"
REQUEST_TIMEOUT = 300
MAX_RETRIES = 1

# 批处理配置
DEFAULT_BATCH_SIZE = 32

# 向量维度配置
VECTOR_DIM = 1024 