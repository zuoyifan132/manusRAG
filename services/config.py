# The IPs that allowed to access the services
allowed_ips = [
    "10.100.167.66",
    "10.106.51.224",
    "10.100.167.118",
    "10.100.3.108",
    "127.0.0.1"
]

# Embedding and reranker service URL
RERANKER_API_URL = "http://127.0.0.1:12212/rerank"
EMBEDDING_API_URL = "http://127.0.0.1:12212/bge_m3_embedding"
MINERU_API_URL = "http://127.0.0.1:8888/file_parse"
OPENAI_API_KEY = ""

MILVUS_RETRY_WAIT_TIME = 1
MILVUS_RETRY_TIMES = 3