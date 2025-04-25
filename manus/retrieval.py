import os
from typing import  List

import sys
sys.path.append("..")

from webui.core import flash_rag


DIR_PATH = os.path.dirname(os.path.abspath(__file__))
default_config_path = os.path.join(DIR_PATH, "../examples/search_example_config.json")
    

def flash_rag_searcher(query: str) -> tuple[str, List]:
    """
    基于flash_rag的search_data的RAG服务的查询.

    :param query: 问题.
    :return: 答案和相关文档的元组.
    """
    try:        
        # 使用flash_rag的search_data函数进行数据召回
        results = flash_rag.search_data(query, config=default_config_path)
        
        # 如果没有检索到结果，返回错误信息
        if not results:
            return "text", ["flash_rag_searcher: 未找到相关文档"]
        
        # 格式化返回的文档列表
        docs = []
        for item in results:
            # 从每个结果中提取内容
            doc_content = item.get("内容", "")
            if doc_content:
                docs.append(doc_content)
        
        # 如果没有有效内容，返回错误信息
        if not docs:
            return "text", ["flash_rag_searcher: 检索结果不包含有效内容"]
            
        # 返回数据格式为 ("text", [文档列表])
        return "text", docs
        
    except Exception as exc:
        # 发生异常时返回错误信息
        return "text", [f"flash_rag_searcher: 工具执行失败! 错误: {str(exc)}"]


if __name__ == "__main__":
    print(flash_rag_searcher("中国2023GDP"))
