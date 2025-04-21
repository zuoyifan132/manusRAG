import sys

sys.path.append(".")
sys.path.append("..")

import time
import json
import requests
from loguru import logger
from rerank.bgem3v2Reranker import BGEM3V2Reranker


if __name__ == "__main__":
    # Testing code: instantiate and call BGEM3V2Reranker
    test_query = "What is the weather like?"
    test_sentences = [
        "The weather is lovely today.",
        "It's so sunny outside!",
        "He drove to the stadium.",
        "今儿天气真的好啊，适合出去玩",
        "你妈喊你回家吃饭"
    ]

    reranker = BGEM3V2Reranker()

    # Call the rerank method
    rerank_results = reranker.rerank(query=test_query, top_k=2, sentences=test_sentences)
    
    if rerank_results:
        print("\nReranked Results:")
        for result in rerank_results:
            print(f"Sentence: {result.get('sentence')}")
            print(f"Score: {result.get('score', 0.0):.4f}")
            print("-" * 40)
    else:
        print("Failed to call the Reranker API.")