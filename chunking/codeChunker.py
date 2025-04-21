import re
import sys

sys.path.append(".")
sys.path.append("..")

from typing import List, Union, Literal, Any
from chunking.textChunker import RecursiveChunker
from chunking.baseChunker import Document


# 新增的 PythonChunker，继承自 RecursiveChunker
class PythonChunker(RecursiveChunker):
    """一个针对 Python 代码的递归文本切分器，继承自 RecursiveChunker。"""
    
    PYTHON_SEPARATORS = [
        "\nclass ",    # 类定义
        "\ndef ",      # 函数定义
        "\n\tdef ",    # 类中的方法定义
        "\n\n",        # 段落分隔
        "\n",          # 行分隔
        " ",           # 空格
        ""             # 空字符串作为最后手段
    ]

    def __init__(
        self,
        chunk_size: int = 100,
        keep_separator: Union[bool, Literal["start", "end"]] = True,
        is_separator_regex: bool = False,
        length_function: callable = len
    ) -> None:
        """初始化 PythonChunker，使用 Python 特定的分隔符。
        
        Args:
            chunk_size (int): 最大块大小，默认 100。
            keep_separator (Union[bool, Literal["start", "end"]]): 是否保留分隔符，默认 True。
            is_separator_regex (bool): 分隔符是否为正则表达式，默认 False。
            length_function (callable): 计算文本长度的函数，默认 len。
        """
        # 调用 RecursiveChunker 的 __init__，传入 Python 特定的分隔符
        super().__init__(
            chunk_size=chunk_size,
            separators=self.PYTHON_SEPARATORS,
            keep_separator=keep_separator,
            is_separator_regex=is_separator_regex,
            length_function=length_function
        )

    def chunk(self, text: str, title: str = "", **kwargs) -> List[Document]:
        """实现 BaseChunker 的抽象方法，用于将 Python 代码切分成小块。
        
        Args:
            text (str): 要切分的 Python 代码
            title (str): 文档标题，默认为空字符串
            **kwargs: 可选参数，当前未使用。
        
        Returns:
            List[Document]: 包含分割后的代码块和元数据的文档对象列表。
        """
        chunks = self._split_text(text, self._separators)
        # 过滤掉空的chunk
        chunks = [chunk for chunk in chunks if chunk.strip()]
        # 创建文档列表
        documents = [Document(chunk=chunk, metadata={"title": title}) for chunk in chunks]
        return documents

# 示例使用
if __name__ == "__main__":
    # 测试 Python 代码
    python_code = """
# this is my code
class MyClass:
    def method1(self):
        print("Hello")
        
    def method2(self):
        print("World")

def standalone_function():
    print("Test")
    
class AnotherClass:
    def another_method(self):
        return "Another"
    """

    # 创建 PythonChunker 实例
    chunker = PythonChunker(chunk_size=100, keep_separator=True)
    
    # 调用 chunk 方法
    documents = chunker.chunk(text=python_code, title="test.py")
    
    # 输出结果
    print(f"文档数量: {len(documents)}")
    for i, doc in enumerate(documents):
        print(f"chunk {i}: {doc.chunk!r}")
        print(f"metadata: {doc.metadata}")
        print("-" * 50)
    
    # 计算平均长度
    avg_length = sum(len(doc.chunk) for doc in documents) / len(documents) if documents else 0
    print(f"平均长度: {avg_length}")