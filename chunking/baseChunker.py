from abc import ABC, abstractmethod
from typing import Dict, Any, List


class Document:
    def __init__(self, chunk: str, metadata: Dict[str, Any]):
        self.chunk = chunk
        self.metadata = metadata

    def format_chunk(self) -> str:
        """将 metadata 中的键值对按照顺序添加到 chunk 内容的前面。
        
        Returns:
            str: 格式化后的文本，包含 metadata 信息和原始 chunk 内容。
        """
        # 将 metadata 中的键值对转换为字符串
        metadata_copy = self.metadata.copy() 
        metadata_copy.update({"title": metadata_copy["title"].split("/")[-1]})
        metadata_str = "\n".join([f"{key}: {value}" for key, value in metadata_copy.items()])
        # 将 metadata 信息和原始 chunk 内容组合
        return f"{metadata_str}\n\n{self.chunk}"


class BaseChunker(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def chunk(self, text: str, title: str = "", **kwargs) -> List[Document]:
        """
        按字符分块并返回结果。
        
        Args:
            text (str): 要切分的文本
            title (str): 文档标题，默认为空字符串
            **kwargs: 其他可选参数
        """
        pass