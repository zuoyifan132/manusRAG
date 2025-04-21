"""
@File   : bge_m3_embedding.py
@Time   : 2025/03/11 15:45
@Author : yfzuo
@Desc   : BGE-M3 和 OpenAI 嵌入API调用
"""
import sys
import json
from typing import List, Optional
import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from pymilvus.model import DefaultEmbeddingFunction
import numpy as np
from openai import OpenAI

sys.path.append("..")

from eval.utilities import cosine_similarity
from database.milvus.config import REQUEST_TIMEOUT, MAX_RETRIES
from services.config import EMBEDDING_API_URL, OPENAI_API_KEY
from database.milvus.config import VECTOR_DIM


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
def bge_m3_embedding_api(texts: List[str]) -> Optional[List[List[float]]]:
    """
    调用BGE-M3 API生成文本嵌入向量
    
    Args:
        texts: 需要生成嵌入向量的文本列表
        
    Returns:
        嵌入向量列表，如果请求失败则返回None
    """
    if not texts or not all(isinstance(text, str) and text.strip() for text in texts):
        logger.error("输入文本无效")
        return None
        
    headers = {"content-type": "application/json;charset=utf-8"}
    body = {"texts": texts}
    
    try:
        response = requests.post(
            url=EMBEDDING_API_URL,
            data=json.dumps(body),
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.error(f"API请求失败: {response.status_code}\n响应数据: {response.text}")
            return None
            
        response_data = response.json()
        return response_data.get("data")
        
    except requests.exceptions.Timeout:
        logger.error("API请求超时")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"API请求异常: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"处理响应时发生错误: {str(e)}")
        return None


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
def openai_embedding_api(texts: List[str], model: str = "text-embedding-3-large") -> Optional[List[List[float]]]:
    """
    调用OpenAI API生成文本嵌入向量（优化版）
    
    Args:
        texts: 需要生成嵌入向量的文本列表
        model: OpenAI嵌入模型名称，默认使用text-embedding-3-large
        dimensions: 可选，指定嵌入向量的维度（用于降维）
        
    Returns:
        嵌入向量列表，如果请求失败则返回None
    """
    if not texts or not all(isinstance(text, str) and text.strip() for text in texts):
        logger.error("输入文本无效")
        return None
        
    try:
        # 初始化 OpenAI 客户端
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # 准备请求参数
        params = {
            "model": model,
            "input": texts,
            "dimensions": VECTOR_DIM
        }
        
        # 创建嵌入向量
        response = client.embeddings.create(**params)
        
        # 提取嵌入向量
        embeddings = [data.embedding for data in response.data]
        return embeddings
        
    except Exception as e:
        logger.error(f"OpenAI API请求异常: {str(e)}")
        return None


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
def milvus_model_embedding(texts: List[str]) -> Optional[List[List[float]]]:
    """
    使用Milvus内置的嵌入模型生成文本嵌入向量
    
    Args:
        texts: 需要生成嵌入向量的文本列表
        
    Returns:
        嵌入向量列表，如果请求失败则返回None
    """
    if not texts or not all(isinstance(text, str) and text.strip() for text in texts):
        logger.error("输入文本无效")
        return None
        
    try:
        # 使用pymilvus内置的DefaultEmbeddingFunction来生成嵌入向量
        ef = DefaultEmbeddingFunction()
        embeddings = ef.encode_documents(texts)
        return embeddings
        
    except Exception as e:
        logger.error(f"使用Milvus嵌入模型时发生错误: {str(e)}")
        return None


if __name__ == "__main__":
    # 测试两个句子的相似度
    test_texts = ["我想吃饭", "我不想吃什么"]
    
    # # 使用BGE-M3生成嵌入向量
    # embeddings = bge_m3_embedding_api(texts=test_texts)
    # if embeddings:
    #     print(f"BGE-M3生成的嵌入向量数量: {len(embeddings)}")
    #     # 使用cosine_similarity计算相似度
    #     similarity = cosine_similarity(embeddings[0], embeddings[1])
    #     print(f"句子相似度(BGE-M3): {similarity:.4f}")
    # else:
    #     print("BGE-M3生成嵌入向量失败")
    
    # 测试OpenAI嵌入模型
    openai_embeddings = openai_embedding_api(texts=test_texts, model="text-embedding-3-small", dimensions=1024)
    if openai_embeddings:
        print(len(openai_embeddings[0]))
        print(f"OpenAI生成的嵌入向量数量: {len(openai_embeddings)}")
        # 使用cosine_similarity计算相似度
        openai_similarity = cosine_similarity(openai_embeddings[0], openai_embeddings[1])
        print(f"句子相似度(OpenAI): {openai_similarity:.4f}")
    else:
        print("OpenAI生成嵌入向量失败")
        
    # 测试Milvus嵌入模型
    # milvus_embeddings = milvus_model_embedding(texts=test_texts)
    # if milvus_embeddings:
    #     print(f"Milvus生成的嵌入向量数量: {len(milvus_embeddings)}")
    #     # 使用cosine_similarity计算相似度
    #     milvus_similarity = cosine_similarity(milvus_embeddings[0], milvus_embeddings[1])
    #     print(f"句子相似度(Milvus): {milvus_similarity:.4f}")
    # else:
    #     print("Milvus生成嵌入向量失败")
# %%
