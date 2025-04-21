from loguru import logger
from typing import List, Dict, Optional
from rerank.baseReranker import BaseReranker
from utils.reranker_api import reranker_api


# Define BGEM3V2Reranker class inheriting from BaseReranker
class BGEM3V2Reranker(BaseReranker):
    """
    Implementation of a Reranker using the BGE-M3V2 model.
    """
    def rerank(self, query: str, top_k: int, sentences: List[str]) -> Optional[List[Dict[str, float]]]:
        """
        Use the Reranker API to re-rank sentences.
        Args:
            query (str): Query string.
            top_k (int): Number of top results to return.
            sentences (List[str]): List of candidate sentences.

        Returns:
            Optional[List[Dict[str, float]]]: List of re-ranked sentences and their scores.
        """
        try:
            # logger.info(f"Calling BGE-M3V2 Reranker API to re-rank. Query: {query}, Top K: {top_k}, Sentences: {sentences}")
            return reranker_api(query=query, top_k=top_k, sentences=sentences)
        except Exception as e:
            logger.error(f"An exception occurred when calling the Reranker API: {str(e)}")
            return None
        

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