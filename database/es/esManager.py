import numpy as np
from tqdm import tqdm
from loguru import logger
from typing import List, Optional
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from database.baseManager import BaseManager
from database.es.config import VECTOR_DIM


class ESManager(BaseManager):
    """
    Elasticsearch 嵌入管理器，继承自 BaseManager。
    管理 Elasticsearch 数据库中的嵌入向量，包括 ingest 和 search 功能。
    """
    def __init__(
            self, 
            collection_name="text_collection", 
            es_host="http://localhost:9200"
        ):
        super().__init__(collection_name=collection_name)

        try:
            # 初始化 Elasticsearch 客户端
            self.client = Elasticsearch([es_host])

            # 确保索引存在，不存在则创建
            if not self.client.indices.exists(index=self.collection_name):
                self._create_index(self.collection_name)
            logger.info(f"成功连接到 Elasticsearch 索引：{self.collection_name}")
        except Exception as e:
            logger.error(f"初始化 Elasticsearch 客户端失败: {str(e)}")
            raise

    def _create_index(self, index_name):
        """
        创建 Elasticsearch 索引，并设置适合嵌入向量的映射。
        
        参数:
            index_name (str): 索引名称。
        """
        try:
            # 定义索引映射
            mapping = {
                "mappings": {
                    "properties": {
                        "vector": {
                            "type": "dense_vector",
                            "dims": VECTOR_DIM,
                            "index": True,
                            "similarity": "cosine"  # 使用余弦相似度
                        },
                        "text": {
                            "type": "text"
                        }
                    }
                }
            }
            self.client.indices.create(index=index_name, body=mapping)
            logger.info(f"成功为索引 {index_name} 创建映射")
        except Exception as e:
            logger.error(f"创建索引时发生错误: {str(e)}")
            raise

    def ingest(self, texts: List[str], batch_size_limit: int=16):
        """
        处理并存储批量文本到 Elasticsearch。
        如果超过批量大小限制，则分批处理。
        
        参数:
            texts (list): 要处理和存储的文本块列表。
        """
        if len(texts) > batch_size_limit:
            # 分批处理
            for i in range(0, len(texts), batch_size_limit):
                batch = texts[i:i + batch_size_limit]
                self._ingest_batch(batch)
        else:
            self._ingest_batch(texts)

    def _ingest_batch(self, texts: List[str]):
        """
        辅助方法，处理并存储单个批次的文本。
        生成嵌入向量并插入到 Elasticsearch。
        
        参数:
            texts (list): 文本批次。
        """
        try:
            # 生成嵌入向量
            embeddings = self.embedding(texts=texts)
            
            # 批量构造数据
            actions = []
            for text, vector in tqdm(zip(texts, embeddings), total=len(texts)):
                actions.append({
                    "_op_type": "index",
                    "_index": self.collection_name,
                    "_source": {
                        "vector": vector,
                        "text": text
                    }
                })
            
            # 批量插入数据
            bulk(self.client, actions)
            logger.info(f"成功插入 {len(texts)} 条数据到索引 {self.collection_name}")
        except Exception as e:
            logger.error(f"插入过程发生错误: {str(e)}")

    def search(self, query: str, top_k: int = 3) -> Optional[List[str]]:
        """
        执行 top-k 相似性搜索。
        返回索引中与查询最相似的 top-k 文本。
        
        参数:
            query (str): 查询文本。
        
        返回:
            top-k 相似文本列表，如果搜索失败则返回 None。
        """
        if not query or not query.strip():
            logger.error("查询文本不能为空")
            return None
            
        try:
            # 为查询生成嵌入向量
            query_embedding = self.embedding([query])
            if not query_embedding:
                logger.error("生成查询嵌入向量失败")
                return None

            # 构造搜索请求
            search_query = {
                "size": top_k,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",  # 余弦相似度
                            "params": {
                                "query_vector": query_embedding[0]
                            }
                        }
                    }
                },
                "_source": ["text"]  # 返回文本字段
            }

            # 执行搜索
            response = self.client.search(index=self.collection_name, body=search_query)

            # 提取并返回文本
            hits = response.get("hits", {}).get("hits", [])
            return [hit["_source"]["text"] for hit in hits]
            
        except Exception as e:
            logger.error(f"搜索过程发生错误: {str(e)}")
            return None
