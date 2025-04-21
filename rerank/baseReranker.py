from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from loguru import logger

# Define the BaseReranker abstract base class
class BaseReranker(ABC):
    """
    Abstract base class defining the essential interface for a Reranker.
    """
    @abstractmethod
    def rerank(self, query: str, top_k: int, sentences: List[str]) -> Optional[List[Dict[str, float]]]:
        """
        Re-rank candidate sentences.
        Args:
            query (str): Query string.
            top_k (int): Number of top results to return.
            sentences (List[str]): List of candidate sentences.

        Returns:
            Optional[List[Dict[str, float]]]: List of re-ranked sentences and their scores.
        """
        pass
