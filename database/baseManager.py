from abc import ABC, abstractmethod
from typing import List, Optional


class BaseManager(ABC):
    """
    抽象基类，用于定义通用的嵌入管理器接口。
    """
    def __init__(self, collection_name: str):
        """
        初始化基础管理器。
        
        参数:
            collection_name (str): 集合名称。
            batch_size_limit (int): 最大批量处理大小。
        """
        self.collection_name = collection_name

    @abstractmethod
    def ingest(self, texts: List[str], batch_size_limit: int=16):
        """
        抽象方法：处理并存储批量文本到数据库。
        
        参数:
            texts (list): 要处理和存储的文本块列表。
        """
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 3) -> Optional[List[str]]:
        """
        抽象方法：查询文本在数据库中的相似项。
        
        参数:
            query (str): 查询文本。
            top_k (int): 检索结果数量。
        
        返回:
            相似文本列表。
        """
        pass