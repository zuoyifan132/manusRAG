"""
@File   : reranker_service.py
@Time   : 2025/04/08 16:30
@Author : yfzuo
@Desc   : Reranker 服务API调用
"""
import sys

sys.path.append(".")
sys.path.append("..")

import json
from typing import List, Optional, Dict
import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from rerank.config import REQUEST_TIMEOUT, MAX_RETRIES
from services.config import RERANKER_API_URL


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
def reranker_api(query: str, top_k: int, sentences: List[str]) -> Optional[List[Dict[str, float]]]:
    """
    调用 Reranker API 对候选句子进行重新排序
    
    Args:
        query: 查询文本字符串
        sentences: 需要排序的候选句子列表

    Returns:
        重新排序的结果列表（包含句子及其分数），如果请求失败则返回 None
    """
    if not query or not query.strip():
        logger.error("输入的查询无效")
        return None
    
    if not sentences or not all(isinstance(sentence, str) and sentence.strip() for sentence in sentences):
        logger.error("输入的候选句子无效")
        return None

    headers = {"Content-Type": "application/json"}
    body = {
        "query": query, 
        "top_k": top_k,
        "sentences": sentences
    }

    try:
        response = requests.post(
            url=RERANKER_API_URL,
            json=body,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            logger.error(f"API请求失败: {response.status_code}\n响应数据: {response.text}")
            return None

        response_data = response.json()

        if "results" not in response_data:
            logger.error("API响应格式错误，缺少 'results' 字段")
            return None

        return response_data.get("results")

    except requests.exceptions.Timeout:
        logger.error("API请求超时")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"API请求异常: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"处理响应时发生错误: {str(e)}")
        return None


if __name__ == "__main__":
    # 测试代码
    test_query = "What is the weather like?"
    test_sentences = [
        "The weather is lovely today.",
        "It's so sunny outside!",
        "He drove to the stadium.",
        "今儿天气真的好啊，适合出去玩",
        "你妈喊你回家吃饭"
    ]

    # 调用 Reranker API
    rerank_results = reranker_api(
        query=test_query, 
        top_k=2, 
        sentences=test_sentences
    )
    if rerank_results:
        print("\nReranked Results:")
        for result in rerank_results:
            print(f"Sentence: {result.get('sentence')}")
            print(f"Score: {result.get('score', 0.0):.4f}")
            print("-" * 40)
    else:
        print("调用 Reranker API 失败")
