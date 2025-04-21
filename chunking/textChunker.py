import re
import sys

sys.path.append(".")
sys.path.append("..")

from typing import List, Union, Literal, Any
from chunking.baseChunker import BaseChunker
from chunking.baseChunker import Document


class PunctuationChunker(BaseChunker):
    def __init__(
            self, 
            punctuation_set=None
        ):
        super().__init__()
        self.punctuation_set = punctuation_set if punctuation_set else {'.', ',', '!', '?', ';', "。", "，"}

    def chunk(self, text: str, title: str = "", **kwargs) -> List[Document]:
        """
        按字符分块，确保在标点符号处分割，块大小在 min_chunk_size 和 max_chunk_size 之间，
        并支持 overlap_chunk_size 的重叠功能。
        """
        min_chunk_size = kwargs.get("min_chunk_size")
        max_chunk_size = kwargs.get("max_chunk_size")
        overlap_chunk_size = kwargs.get("overlap_chunk_size")

        # 参数验证
        if min_chunk_size is None or max_chunk_size is None or overlap_chunk_size is None:
            raise ValueError("min_chunk_size, max_chunk_size, and overlap_chunk_size are required parameters")

        if min_chunk_size <= 0 or max_chunk_size <= 0 or overlap_chunk_size < 0:
            raise ValueError("min_chunk_size 和 max_chunk_size 必须为正数，overlap_chunk_size 必须为非负数")
        if min_chunk_size > max_chunk_size:
            raise ValueError("min_chunk_size 必须小于或等于 max_chunk_size")
        if overlap_chunk_size >= max_chunk_size:
            raise ValueError("overlap_chunk_size 必须小于 max_chunk_size")
        # 如果文本长度小于 min_chunk_size，直接返回整个文本
        if len(text) < min_chunk_size:
            return [Document(chunk=text, metadata={"title": title})]

        chunks = []
        start = 0
        text_length = len(text)
        while start < text_length:
            # 确定当前块的结束位置，必须在标点符号处
            end = self._find_next_punctuation(text, start, min_chunk_size, max_chunk_size)
            if end == -1:  # 没有找到标点符号
                end = text_length  # 分到文本末尾
            # 提取当前块
            chunk = text[start:end]
            chunks.append(Document(chunk=chunk, metadata={"title": title}))
            # 如果到达文本末尾，退出循环
            if end == text_length:
                break
            # 计算下一个块的起始位置，考虑重叠
            start = end - overlap_chunk_size

        # 处理最后一个块小于 min_chunk_size 的情况
        if len(chunks) > 1 and len(chunks[-1].chunk) < min_chunk_size:
            last_chunk = chunks.pop()
            chunks[-1] = Document(
                chunk=chunks[-1].chunk + last_chunk.chunk,
                metadata={"title": title}
            )
        return chunks
    
    def _find_next_punctuation(self, text: str, start: int, min_chunk_size: int, max_chunk_size: int):
        """
        在 [start + min_chunk_size, start + max_chunk_size] 范围内寻找第一个标点符号的位置。
        如果没有找到，返回 -1。
        """
        min_end = start + min_chunk_size
        max_end = min(start + max_chunk_size, len(text))
        for i in range(min_end, max_end):
            if text[i] in self.punctuation_set:
                return i + 1  # 返回标点符号后的位置
        # 如果在范围内没有标点符号，继续向后找第一个标点符号
        for i in range(max_end, len(text)):
            if text[i] in self.punctuation_set:
                return i + 1
        return -1  # 没有找到标点符号
    

class RecursiveChunker(BaseChunker):
    """一个简单的递归文本切分器，继承自 BaseChunker。"""
    
    def __init__(
        self,
        chunk_size: int = 100,
        separators: List[str] = None,
        keep_separator: Union[bool, Literal["start", "end"]] = True,
        is_separator_regex: bool = False,
        length_function: callable = len,
        overlap_chunk_size: int = 0
    ) -> None:
        """初始化 RecursiveChunker。
        
        Args:
            chunk_size (int): 最大块大小，默认 100。
            separators (List[str]): 分隔符列表，默认 ["\n\n", "\n", " ", ""]。
            keep_separator (Union[bool, Literal["start", "end"]]): 是否保留分隔符，默认 True。
            is_separator_regex (bool): 分隔符是否为正则表达式，默认 False。
            length_function (callable): 计算文本长度的函数，默认 len。
            overlap_chunk_size (int): 文本块重叠的大小，默认为0(不重叠)。
        """
        super().__init__()
        self._chunk_size = chunk_size
        self._separators = separators or ["\n\n", "\n", "。", ".", "！", "！", ";", "；", "?", "？", ",", "，", "、", " ", ""]
        self._keep_separator = keep_separator
        self._is_separator_regex = is_separator_regex
        self._length_function = length_function
        self._overlap_chunk_size = overlap_chunk_size

    def _split_text_with_regex(self, text: str, separator: str) -> List[str]:
        """辅助方法：使用正则表达式分割文本，并根据 keep_separator 处理分隔符。"""
        if self._keep_separator == "start":
            splits = re.split(f"({separator})", text)
            return [splits[i] + splits[i + 1] if i + 1 < len(splits) else splits[i] for i in range(0, len(splits) - 1, 2)]
        elif self._keep_separator == "end":
            splits = re.split(f"({separator})", text)
            return [splits[i] + splits[i + 1] if i + 1 < len(splits) else splits[i] for i in range(0, len(splits), 2)]
        elif self._keep_separator:
            splits = re.split(f"({separator})", text)
            return [s + sep for s, sep in zip(splits[::2], splits[1::2] + [""])]
        else:
            return re.split(separator, text)

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """辅助方法：合并小的文本块。"""
        result = []
        current_chunk = ""
        for s in splits:
            if self._length_function(current_chunk + separator + s) < self._chunk_size:
                current_chunk += (separator + s if current_chunk else s)
            else:
                if current_chunk:
                    result.append(current_chunk)
                current_chunk = s
        if current_chunk:
            result.append(current_chunk)
        return result

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """核心递归切分逻辑。"""
        final_chunks = []
        # 选择合适的 separator
        separator = separators[-1]
        new_separators = []
        for i, _s in enumerate(separators):
            _separator = _s if self._is_separator_regex else re.escape(_s)
            if _s == "":
                separator = _s
                break
            if re.search(_separator, text):
                separator = _s
                new_separators = separators[i + 1:]
                break

        # 处理分隔符是否为正则表达式
        _separator = separator if self._is_separator_regex else re.escape(separator)
        splits = self._split_text_with_regex(text, _separator)

        # 合并和递归分割
        _good_splits = []
        _separator = "" if self._keep_separator else separator
        for s in splits:
            if self._length_function(s) < self._chunk_size:
                _good_splits.append(s)
            else:
                if _good_splits:
                    merged_text = self._merge_splits(_good_splits, _separator)
                    final_chunks.extend(merged_text)
                    _good_splits = []
                if not new_separators:
                    final_chunks.append(s)
                else:
                    other_info = self._split_text(s, new_separators)
                    final_chunks.extend(other_info)
        if _good_splits:
            merged_text = self._merge_splits(_good_splits, _separator)
            final_chunks.extend(merged_text)

        return final_chunks

    def chunk(self, text: str, title: str = "", **kwargs) -> List[Document]:
        """实现 BaseChunker 的抽象方法，用于将文本切分成小块。
        
        Args:
            text (str): 要切分的文本
            title (str): 文档标题，默认为空字符串
            **kwargs: 可选参数，可包含 overlap_chunk_size 覆盖初始设置的重叠大小。
        
        Returns:
            List[Document]: 包含分割后的文本块和元数据的文档对象列表。
        """
        # 允许通过kwargs覆盖初始设置的overlap_chunk_size
        overlap_chunk_size = kwargs.get("overlap_chunk_size", self._overlap_chunk_size)
        
        chunks = self._split_text(text, self._separators)
        # 过滤掉空的chunk
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        # 如果没有设置重叠或只有一个chunk，直接返回
        if overlap_chunk_size <= 0 or len(chunks) <= 1:
            documents = [Document(chunk=chunk, metadata={"title": title}) for chunk in chunks]
            return documents
        
        # 处理重叠
        documents = []
        for i, chunk in enumerate(chunks):
            # 获取扩展文本
            expanded_chunk = chunk
            
            # 向上文扩展
            if i > 0:
                prev_chunk = chunks[i-1]
                # 计算最大可扩展长度
                max_overlap = min(overlap_chunk_size, len(prev_chunk))
                
                # 从后向前在前一个chunk中寻找分隔符
                overlap_start = len(prev_chunk) - max_overlap
                prefix = prev_chunk[overlap_start:]
                
                # 检查是否包含分隔符，如果包含，从分隔符处截断
                for separator in self._separators:
                    if separator and separator in prefix:
                        # 找到最后一个分隔符的位置
                        sep_pos = prefix.rfind(separator)
                        if sep_pos != -1:
                            # 从分隔符后开始取文本
                            prefix = prefix[sep_pos + len(separator):]
                            break
                
                expanded_chunk = prefix + expanded_chunk
                
            # 向下文扩展
            if i < len(chunks) - 1:
                next_chunk = chunks[i+1]
                # 计算最大可扩展长度
                max_overlap = min(overlap_chunk_size, len(next_chunk))
                
                # 取下一个chunk的前max_overlap个字符
                suffix = next_chunk[:max_overlap]
                
                # 检查是否包含分隔符，如果包含，从分隔符处截断
                for separator in self._separators:
                    if separator and separator in suffix:
                        # 找到第一个分隔符的位置
                        sep_pos = suffix.find(separator)
                        if sep_pos != -1:
                            # 只取到分隔符前的文本
                            suffix = suffix[:sep_pos]
                            break
                
                expanded_chunk = expanded_chunk + suffix
            
            documents.append(Document(chunk=expanded_chunk, metadata={"title": title}))
        
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
    
    # # 创建 RecursiveChunker 实例
    # chunker = RecursiveChunker(chunk_size=200)
    
    # # 调用 chunk 方法
    # documents = chunker.chunk(text=sample_text, title="测试文档.txt")
    
    # # 输出结果
    # print(f"文档数量: {len(documents)}")
    # for i, doc in enumerate(documents):
    #     print(f"chunk {i}: {doc.chunk}")
    #     print(f"metadata: {doc.metadata}")
    #     print(f"formatted chunk: \n{doc.format_chunk()}")
    #     print("-" * 50)

    # # 计算平均长度
    # average_length = sum(len(doc.chunk) for doc in documents) / len(documents)
    # print(f"平均长度: {average_length}")

    # print("=" * 50)
    # print("测试 PunctuationChunker:")
    # # 创建 PunctuationChunker 实例
    # punctuation_chunker = PunctuationChunker()
    # documents = punctuation_chunker.chunk(
    #     text=sample_text, 
    #     title="测试文档", 
    #     min_chunk_size=100, 
    #     max_chunk_size=200, 
    #     overlap_chunk_size=50
    # )
    
    # # 输出结果
    # print(f"文档数量: {len(documents)}")
    # for i, doc in enumerate(documents):
    #     print(f"chunk {i}: {doc.chunk}")
    #     print(f"metadata: {doc.metadata}")
    #     print(f"formatted chunk: \n{doc.format_chunk()}")
    #     print("-" * 50)
    
    print("=" * 50)
    print("测试 RecursiveChunker 的 overlap_chunk_size 功能:")
    # 创建带有重叠的 RecursiveChunker 实例
    overlap_chunker = RecursiveChunker(chunk_size=200, overlap_chunk_size=50)
    
    # 调用 chunk 方法
    documents = overlap_chunker.chunk(text=sample_text, title="测试文档-重叠版.txt")
    
    # 输出结果
    print(f"文档数量: {len(documents)}")
    for i, doc in enumerate(documents):
        print(f"chunk {i}: {doc.chunk}")
        print(f"metadata: {doc.metadata}")
        print(f"formatted chunk: \n{doc.format_chunk()}")
        print("-" * 50)
    
    # 计算带重叠的平均长度
    average_length = sum(len(doc.chunk) for doc in documents) / len(documents)
    print(f"带重叠的平均长度: {average_length}")
    
    # # 测试通过kwargs设置overlap_chunk_size
    # print("=" * 50)
    # print("测试通过kwargs设置overlap_chunk_size:")
    # chunker = RecursiveChunker(chunk_size=200)  # 初始不设置重叠
    # documents = chunker.chunk(
    #     text=sample_text, 
    #     title="测试文档-kwargs重叠版.txt",
    #     overlap_chunk_size=30  # 通过kwargs设置重叠
    # )
    
    # print(f"文档数量: {len(documents)}")
    # for i, doc in enumerate(documents):
    #     print(f"chunk {i}: {doc.chunk}")
    #     print(f"metadata: {doc.metadata}")
    #     print("-" * 50)
    
    # # 计算通过kwargs设置重叠的平均长度
    # average_length = sum(len(doc.chunk) for doc in documents) / len(documents)
    # print(f"通过kwargs设置重叠的平均长度: {average_length}")