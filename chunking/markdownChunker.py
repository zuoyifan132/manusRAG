import sys

sys.path.append(".")
sys.path.append("..")

from typing import List, Union, Literal, Any, Dict
from chunking.baseChunker import BaseChunker
from chunking.baseChunker import Document
from chunking.textChunker import RecursiveChunker


class MarkdownChunker(BaseChunker):
    """Markdown文档标题分割器
    
    用于根据指定的标题层级对Markdown文档进行分割，每个分割后的块都包含相应的标题元数据。
    """

    def __init__(
        self,
        markdown_headers_to_split_on: List[tuple[str, str]],
        return_each_line: bool = False,
        strip_headers: bool = True,
        markdown_chunk_limit: int = 200,
    ):
        """初始化Markdown标题分割器

        Args:
            markdown_headers_to_split_on: 要分割的标题列表，每个元素为(标题标记, 标题名称)的元组
                例如: [("#", "h1"), ("##", "h2")]
            return_each_line: 是否返回每行内容，如果为False则返回聚合后的内容块
            strip_headers: 是否从内容中移除标题行
            markdown_chunk_limit: 当块长度超过此值时，使用 RecursiveChunker 进行进一步切分
        """
        super().__init__()
        self.return_each_line = return_each_line
        # 对标题标记按长度降序排序，确保更长的标题标记优先匹配
        self.markdown_headers_to_split_on = sorted(
            markdown_headers_to_split_on, key=lambda split: len(split[0]), reverse=True
        )
        self.strip_headers = strip_headers
        self.markdown_chunk_limit = markdown_chunk_limit
        self.recursive_chunker = RecursiveChunker(chunk_size=markdown_chunk_limit)

    def aggregate_lines_to_chunks(
        self, lines: List[Dict[str, Union[str, Dict[str, str]]]]
    ) -> List[Dict[str, Union[str, Dict[str, str]]]]:
        """将具有相同元数据的连续行聚合为内容块

        Args:
            lines: 包含内容和元数据的行列表，每个元素为{"content": 内容, "metadata": 元数据}

        Returns:
            聚合后的内容块列表
        """
        aggregated_chunks: List[Dict[str, Union[str, Dict[str, str]]]] = []

        for line in lines:
            # 如果当前行与上一个块的元数据相同，则合并内容
            if (
                aggregated_chunks
                and aggregated_chunks[-1]["metadata"] == line["metadata"]
            ):
                aggregated_chunks[-1]["content"] += "  \n" + line["content"]
            # 处理标题层级变化的情况
            elif (
                aggregated_chunks
                and aggregated_chunks[-1]["metadata"] != line["metadata"]
                and len(aggregated_chunks[-1]["metadata"]) < len(line["metadata"])
                and aggregated_chunks[-1]["content"].split("\n")[-1][0] == "#"
                and not self.strip_headers
            ):
                aggregated_chunks[-1]["content"] += "  \n" + line["content"]
                aggregated_chunks[-1]["metadata"] = line["metadata"]
            # 创建新的内容块
            else:
                aggregated_chunks.append(line)

        return aggregated_chunks
    
    def split_text(self, text: str) -> List[Dict[str, Union[str, Dict[str, str]]]]:
        """分割Markdown文本

        Args:
            text: 要分割的Markdown文本

        Returns:
            分割后的内容块列表，每个块包含内容和元数据
        """
        # 按行分割文本
        lines = text.split("\n")
        # 存储带元数据的行
        lines_with_metadata: List[Dict[str, Union[str, Dict[str, str]]]] = []
        # 当前正在收集的内容
        current_content: List[str] = []
        # 当前块的元数据
        current_metadata: Dict[str, str] = {}
        # 标题栈，用于维护标题层级
        header_stack: List[Dict[str, Union[int, str]]] = []
        # 初始元数据
        initial_metadata: Dict[str, str] = {}

        # 代码块处理相关变量
        in_code_block = False
        opening_fence = ""

        for line in lines:
            # 清理行内容
            stripped_line = line.strip()
            stripped_line = "".join(filter(str.isprintable, stripped_line))
            
            # 处理代码块
            if not in_code_block:
                if stripped_line.startswith("```") and stripped_line.count("```") == 1:
                    in_code_block = True
                    opening_fence = "```"
                elif stripped_line.startswith("~~~"):
                    in_code_block = True
                    opening_fence = "~~~"
            else:
                if stripped_line.startswith(opening_fence):
                    in_code_block = False
                    opening_fence = ""

            # 如果是代码块中的内容，直接添加到当前内容
            if in_code_block:
                current_content.append(stripped_line)
                continue

            # 检查是否是标题行
            for sep, name in self.markdown_headers_to_split_on:
                if stripped_line.startswith(sep) and (
                    len(stripped_line) == len(sep) or stripped_line[len(sep)] == " "
                ):
                    if name is not None:
                        # 计算当前标题层级
                        current_header_level = sep.count("#")
                        # 清理比当前层级高的标题
                        while (
                            header_stack
                            and header_stack[-1]["level"] >= current_header_level
                        ):
                            popped_header = header_stack.pop()
                            if popped_header["name"] in initial_metadata:
                                initial_metadata.pop(popped_header["name"])

                        # 添加新标题到栈中
                        header = {
                            "level": current_header_level,
                            "name": name,
                            "data": stripped_line[len(sep):].strip(),
                        }
                        header_stack.append(header)
                        initial_metadata[name] = header["data"]

                    # 保存当前收集的内容
                    if current_content:
                        lines_with_metadata.append(
                            {
                                "content": "\n".join(current_content),
                                "metadata": current_metadata.copy(),
                            }
                        )
                        current_content.clear()

                    # 如果不移除标题，将标题添加到内容中
                    if not self.strip_headers:
                        current_content.append(stripped_line)

                    break
            else:
                # 处理普通文本行
                if stripped_line:
                    current_content.append(stripped_line)
                elif current_content:
                    # 遇到空行时保存当前内容
                    lines_with_metadata.append(
                        {
                            "content": "\n".join(current_content),
                            "metadata": current_metadata.copy(),
                        }
                    )
                    current_content.clear()

            # 更新当前元数据
            current_metadata = initial_metadata.copy()

        # 处理最后的内容块
        if current_content:
            lines_with_metadata.append(
                {
                    "content": "\n".join(current_content),
                    "metadata": current_metadata,
                }
            )

        # 根据设置返回每行内容或聚合后的内容块
        if not self.return_each_line:
            return self.aggregate_lines_to_chunks(lines_with_metadata)
        else:
            return lines_with_metadata
        
    def chunk(self, text: str, title: str = "", **kwargs) -> List[Document]:
        """实现 BaseChunker 的抽象方法，用于将Markdown文本切分成小块。
        
        Args:
            text (str): 要切分的Markdown文本
            title (str): 文档标题，默认为空字符串
            **kwargs: 可选参数，当前未使用。
        
        Returns:
            List[Document]: 包含分割后的内容块和元数据的文档对象列表。
        """
        chunks = self.split_text(text)
        # 创建文档列表
        documents = []
        for chunk in chunks:
            # 创建元数据字典，确保 title 在首位
            metadata = {"title": title}
            # 添加其他元数据
            metadata.update(chunk["metadata"])
            
            # 如果内容长度超过限制，使用 RecursiveChunker 进行进一步切分
            if len(chunk["content"]) > self.markdown_chunk_limit:
                recursive_docs = self.recursive_chunker.chunk(
                    text=chunk["content"],
                    title=title,
                    **kwargs
                )
                # 为每个递归切分的文档添加原始元数据
                for doc in recursive_docs:
                    doc.metadata.update(metadata)
                documents.extend(recursive_docs)
            else:
                # 创建文档对象
                doc = Document(chunk=chunk["content"], metadata=metadata)
                documents.append(doc)
        return documents
    

# 示例使用
if __name__ == "__main__":
    # 测试文本
    sample_text = """
### <center>调研报告：DeepSeek-R1 与 Agents 框架结合效率分析<center/>

#### 一句话总结

DeepSeek-R1 在多次调用 ReAct 流程中，首次 Long-CoT 稍长但后续高效，整体性能稳定，适应当前开源框架现状并展现优越推理性能。

#### 背景与目标

本文调研 DeepSeek-R1 与 Agents 框架结合的效果，基于 Dify 底层代码分析其 Agents Workflow 流程，验证 DeepSeek-R1 在多次 Function Calling 场景下的推理效率。目标是评估 Long-CoT（长链推理）和后续 Function Calling 对整体性能的影响，并探讨DeepSeek-R1当前对 ReAct agent流程的支持现状。

#### Dify Agents Workflow 流程

通过分析 Dify 底层代码，其工作流为一个循环过程：

1. 模型生成响应（可能包含工具调用）。
2. 若存在工具调用，执行工具并获取结果。
3. 将工具调用结果加入对话历史。
4. 重新组织提示词（融入工具结果）。
5. 再次调用模型推理。
6. 重复上述步骤，直到模型不再调用工具或达到最大迭代次数。

**补充说明**：与理想的 ReAct 流程（Thought、Action、Observation 拼接为单次模型调用）不同，Dify 及大部分开源框架采用多次模型调用的单轮 ReAct 方式，即每次仅处理一个环节，依赖循环逐步完成任务。所以设想的deepseek能够通过拼接的方式实现效率提升（节省thinking过程）的想法暂不现实。

#### 实验设计

- **模型**：DeepSeek-R1 作为核心大模型。
- **场景**：模拟多次 Function Calling 的任务（如信息检索、数据处理）。
- **关注点**：推理时间，尤其是 Long-CoT 和后续 Function Calling 的时长。
- **假设**：担心多次模型调用（特别是 Long-CoT）会因推理过长降低效率。

#### 实验结果

1. **实验demo(使用DeepSeek-R1)**：

   ```
   🎉 最终结果:
   ========================================
   根据2025年2月27日Wind数据：
   1️⃣ 贵州茅台收盘价：1823元
   2️⃣ 五粮液开盘价：140元
   3️⃣ 今日热点新闻前十：
   ① 全球首辆商业飞行汽车正式上路测试成功  
   ② 某科技公司宣布推出首款量子手机  
   ③ 世界杯预选赛爆冷，强队意外失利  
   ④ 一线城市房价环比下降3%，引发热议  
   ⑤ 某国推出全球首个全民基础收入试点计划  
   ⑥ 全球气温创新高，气候变化议题再引关注  
   ⑦ 某知名AI机器人公司被曝隐私泄露问题  
   ⑧ 某国成功发射载人探测器前往火星  
   ⑨ 新能源车电池技术突破，续航里程翻倍  
   ⑩ 某流行歌手新专辑24小时销量破纪录
   ========================================
   ```

2. **首次调用**：

   - DeepSeek-R1 在首次调用时生成 Long-CoT，推理时间较长（因任务复杂度而异，但显著高于后续调用）。

   - 原因：首次调用需完整分解问题并生成详细推理链。

3. **后续 Function Calling**：

   - 工具调用后，模型基于已有上下文和结果推理。

   - Thinking 和 Reasoning 时间显著缩短，仅为首次调用的 10%-20%。

   - 原因：后续调用依赖已有推理基础，减少重复计算。

4. **效率影响**：

   - Long-CoT 仅在首次调用时显著，后续 Function Calling 的短推理不拖累整体效率。
   - 多次模型调用虽非单次 ReAct，但迭代效率仍高，未见性能明显下降。

#### 结论与亮点

- **高效性验证**：Long-CoT 集中于首次调用，后续 Function Calling 高效。
- **现状反思**：相比于原有的非reasoning系列模型，DeepSeek-R1 的短推理特性弥补了效果短板。
- **适用性**：适合复杂多轮工具调用任务，无需担心推理时长累积。
"""
    
    # 创建 MarkdownChunker 实例
    chunker = MarkdownChunker(
        markdown_headers_to_split_on=[
            ("#", "h1"), 
            ("##", "h2"), 
            ("###", "h3"),
            ("####", "h4"),
            ("#####", "h5"),
            ("######", "h6")
        ],
        strip_headers=True
    )
    
    # 调用 chunk 方法
    documents = chunker.chunk(text=sample_text, title="测试文档.md")
    
    # 输出结果
    print(f"文档数量: {len(documents)}")
    for i, doc in enumerate(documents):
        print(f"chunk {i}: \n{doc.chunk}")
        print(f"metadata: {doc.metadata}")
        print(f"formatted chunk: \n{doc.format_chunk()}")
        print("-" * 50)