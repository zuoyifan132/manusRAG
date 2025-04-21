"""
配置文件
"""
# Milvus配置
MILVUS_HOST = "10.106.51.224"  # Milvus服务器地址
MILVUS_PORT = 19530      # Milvus服务器端口
MILVUS_URI = f"http://{MILVUS_HOST}:{MILVUS_PORT}"  # Milvus连接URI
LOCAL_MILVUS_LITE_DB_PATH = "/Users/evan/Desktop/work/wind/FlashC/rag/database/milvus/milvus_db/milvus_db.db"

# 嵌入API配置
# EMBEDDING_API_URL = "http://10.200.64.10/10-bge-m3/embedding"
EMBEDDING_API_URL = "http://10.100.167.66:13456/bge_m3_embedding"
REQUEST_TIMEOUT = 300
MAX_RETRIES = 1

# 批处理配置
DEFAULT_BATCH_SIZE = 32

# 向量维度配置
VECTOR_DIM = 1024 