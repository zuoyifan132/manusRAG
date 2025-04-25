import os
import json
import uuid
from typing import Dict, List, Optional, Any, Union, Tuple
from pydantic import BaseModel, Field
from tenacity import RetryError
from tqdm import tqdm
from loguru import logger

from services.service import (
    parse_pdf_file,
    parse_doc_file,
    process_chunk_text,
    process_ingest_text,
    process_search_text,
    process_rerank_results,
    ChunkRequest,
    IngestRequest,
    SearchRequest,
    RerankerRequest
)
from utils import aigc_api


class DocToTextConfig(BaseModel):
    """文档转文本配置"""
    strategy: Dict[str, str]
    doc_path: str


class ChunkTextConfig(BaseModel):
    """文本分块配置"""
    file_type: str
    strategy: str
    params: Dict[str, Any] = {}


class IngestTextConfig(BaseModel):
    """文本导入配置"""
    type: str
    params: Dict[str, Any] = {}


class RetrievalConfig(BaseModel):
    """检索配置"""
    type: str
    params: Dict[str, Any] = {}


class RerankConfig(BaseModel):
    """重排序配置"""
    strategy: str
    params: Dict[str, Any] = {}


class AigcConfig(BaseModel):
    """生成模型配置"""
    model: str = "openai"
    aigc_params: Dict[str, Any] = {}


class PipelineConfig(BaseModel):
    """完整的Pipeline配置"""
    doc_2_text: Optional[DocToTextConfig] = None
    chunk_text: Optional[List[ChunkTextConfig]] = None
    ingest_text: Optional[List[IngestTextConfig]] = None
    retrieval: Optional[List[RetrievalConfig]] = None
    rerank: Optional[List[RerankConfig]] = None
    aigc: Optional[AigcConfig] = None
    base_url: Optional[str] = None


# 用于API接口的请求模型
class PipelineRequest(BaseModel):
    """Pipeline API请求模型"""
    config: PipelineConfig
    query: str = "example query"


def process_uploaded_file(file_content: bytes, filename: str, doc_config: DocToTextConfig) -> Tuple[str, Dict[str, Any]]:
    """处理上传的文件并提取文本内容"""
    logger.info(f"处理上传的文件: {filename}")
    
    file_type = filename.split(".")[-1].lower()
    if file_type not in doc_config.strategy:
        error_msg = f"不支持的文件类型: {file_type}"
        logger.error(error_msg)
        return "", {"status": "error", "message": error_msg}
    
    parse_strategy = doc_config.strategy.get(file_type)
    
    try:
        result = parse_doc_file(file_content, filename, parse_strategy)
        extracted_text = result.get("extracted_text", "")
        
        if not extracted_text:
            error_msg = "未能从文件中提取文本"
            logger.error(error_msg)
            return "", {"status": "error", "message": error_msg}
        
        logger.info(f"成功从文件中提取文本，长度: {len(extracted_text)}")
        return extracted_text, {"status": "success", "message": "文本提取成功"}
    except Exception as e:
        error_msg = f"处理文件时发生错误: {str(e)}"
        logger.error(error_msg)
        return "", {"status": "error", "message": error_msg}


def chunk_text(
        config: List[ChunkTextConfig], 
        extracted_text: str, 
        file_type: str = "pdf",
        filename: str = "",
    ) -> List[Dict]:
    """
    文本分块处理
    """
    logger.info("=== 运行文本分块 ===")
    
    # 查找适用于当前文件类型的分块配置
    chunk_config = None
    for cfg in config:
        if cfg.file_type == file_type:
            chunk_config = cfg
            break
    
    if not chunk_config:
        logger.warning(f"未找到适用于 {file_type} 的分块配置")
        return None
    
    request = ChunkRequest(
        text=extracted_text,
        chunk_strategy=chunk_config.strategy,
        title=filename,
        **chunk_config.params
    )
    
    try:
        # 直接调用service.py中的函数
        chunks = process_chunk_text(request)
        chunks_count = len(chunks["data"])
        logger.info(f"分块成功: 共{chunks_count}块")
        return chunks["data"]
    except Exception as e:
        logger.error(f"分块处理错误: {str(e)}")
        return None


def ingest_text(config: List[IngestTextConfig], chunks: List[Dict]) -> bool:
    """文本导入到向量数据库"""
    logger.info("=== 运行文本导入 ===")
    
    if not config:
        logger.warning("未找到导入配置")
        return False
    
    success = True
    
    for ingest_config in config:
        db_type = ingest_config.type
        params = ingest_config.params
        
        # 创建导入请求
        request = IngestRequest(
            chunks_with_metadata=chunks,
            batch_size_limit=params.get("batch_size_limit", 16),
            collection_name=params.get("collection_name", "default"),
            database_strategy=db_type,
            embedding_api=params.get("embedding_api", "openai_embedding_api"),
            expand_fields=params.get("expand_fields", []),
            expand_fields_values=params.get("expand_fields_values", {})
        )
        
        try:
            # 直接调用service.py中的函数
            result = process_ingest_text(request)
            logger.info(f"成功导入到 {db_type}: {result}")
        except RetryError as e:
            logger.error(f"导入到 {db_type} 时错误: {str(e)}")
            success = False
            
    return success


def retrieval(config: List[RetrievalConfig], query: str) -> List[Dict]:
    """从向量数据库检索相关内容"""
    logger.info(f"=== 运行检索，查询: {query} ===")
    
    if not config:
        logger.warning("未找到检索配置")
        return []
    
    all_results = []
    
    for retrieval_config in config:
        db_type = retrieval_config.type
        params = retrieval_config.params
        
        # 创建搜索请求
        request = SearchRequest(
            query=query,
            top_k=params.get("top_k", 10),
            collection_name=params.get("collection_name", "default"),
            database_strategy=db_type
        )
        
        try:
            # 直接调用service.py中的函数
            result = process_search_text(request)
            results = result.get("results", [])
            logger.info(f"从 {db_type} 检索到 {len(results)} 条结果")
            all_results.extend(results)
        except RetryError as e:
            logger.error(f"从 {db_type} 检索时错误: {str(e)}")
    
    return all_results


def rerank(config: List[RerankConfig], query: str, search_results: List[Dict]) -> List[Dict]:
    """对检索结果进行重排序"""
    logger.info("=== 运行重排序 ===")
    
    if not config or not search_results:
        logger.warning("未找到重排序配置或没有检索结果")
        return []
    
    # 使用第一个重排序配置
    rerank_config = config[0]
    strategy = rerank_config.strategy
    params = rerank_config.params
        
    # 创建重排序请求
    request = RerankerRequest(
        query=query,
        chunks_with_metadata=search_results,
        top_k=params.get("top_k", 5),
        rerank_strategy=strategy
    )

    try:
        # 直接调用service.py中的函数
        result = process_rerank_results(request)
        reranked_results = result.get("reranked_results", [])
        logger.info(f"重排序结果数量: {len(reranked_results)}")
        return reranked_results
    except Exception as e:
        logger.error(f"重排序时错误: {str(e)}")
        return []


def generate_answer(config: AigcConfig, query: str, context: List[str]) -> str:
    """使用大模型生成答案"""
    logger.info("=== 运行生成答案 ===")

    system_prompt = (
        f"({{根据以下检索到的相关信息，生成简洁且准确的回答：\n"
        f"请以专业且清晰的语言回答，突出关键点，不加入额外内容。}})"
        f"请将你回答中所用到的信息在Reference区域进行注明,要求追加文档的原文"
        f"请注意所给的文档是结构化的数据：e.g.: markdown # ## etc"
    )

    user_prompt = (
        f"相关信息：{context}\n"
        f"问题：{query}\n"
    )

    if config.model == "deepseek_v3":
        return aigc_api.deepseek_v3_generate(system=system_prompt, user=user_prompt, **config.aigc_params)
    elif config.model == "openai":
        return aigc_api.openai_generate(system=system_prompt, user=user_prompt, **config.aigc_params)
    else:
        logger.warning(f"{config.model} not implemented yet")
        return f"{config.model} not implemented yet"
    

def run_pipeline(
        config: PipelineConfig, 
        file_content: Optional[bytes] = None, 
        filename: Optional[str] = None, 
        query: str = "example query"
    ) -> Dict[str, Any]:
    """
    动化RAG流程
    """
    logger.info(f"--- 开始RAG流程，查询: {query} ---")
    results = {"status": "success"}

    # 步骤1: 如果提供了文件内容，优先处理文件
    if file_content and filename and config.doc_2_text:
        doc_text, status = process_uploaded_file(file_content, filename, config.doc_2_text)
        if status["status"] != "success":
            logger.warning(f"--- 提取失败: {status['message']} ---")
            results["status"] = "failed"
            results["reason"] = status["message"]
            return results
        
        results["extracted_text_length"] = len(doc_text)

    # 步骤2: 文本分块
    all_chunks = []
    if config.chunk_text:
        if doc_text:
            logger.info("处理提取的文本")
            file_type = filename.split(".")[-1].lower() if filename else ""
            chunks = chunk_text(config.chunk_text, doc_text, file_type, filename)
            if chunks:
                all_chunks.extend(chunks)
            
            if not all_chunks:
                logger.warning("--- 分块失败，终止流程... ---")
                results["status"] = "failed"
                results["reason"] = "text chunking failed"
                return results
                
            results["chunks_count"] = len(all_chunks)
        else:
            logger.warning("doc_text is empty")
            return None
            
        # 步骤3: 文本导入到向量数据库
        if config.ingest_text:
            success = ingest_text(config.ingest_text, all_chunks)
            if not success:
                logger.warning("--- 部分数据导入失败，继续流程... ---")
                results["ingest_partial_failed"] = True

    # 步骤4: 检索（如果配置了）
    if config.retrieval:
        search_results = retrieval(config.retrieval, query)
        results["search_results"] = search_results
        results["search_results_count"] = len(search_results)
        
        if not search_results:
            logger.warning("--- 检索失败，终止流程... ---")
            results["status"] = "failed"
            results["reason"] = "retrieval failed"
            return results
            
        # 步骤5: 重排序（如果配置了）
        if config.rerank:
            reranked_results = rerank(config.rerank, query, search_results)
            results["reranked_results"] = reranked_results
            results["reranked_results_count"] = len(reranked_results)
            
            if not reranked_results:
                logger.warning("--- 重排序失败，终止流程... ---")
                results["status"] = "failed"
                results["reason"] = "reranking failed"
                return results
                
            # 步骤6: 生成答案（如果配置了）
            if config.aigc:
                # 选择重排序后的前几个结果作为上下文
                top_contexts = [item.get("chunk", "") for item in reranked_results]
                answer = generate_answer(config.aigc, query, top_contexts)
                results["aigc_answer"] = answer

    logger.info("--- RAG流程完成 ---")
    return results


# 示例用法
if __name__ == "__main__":
    # 加载配置文件示例
    with open("examples/search_example_config.json", "r") as f:
        config_data = json.load(f)
    
    # 解析为Pydantic模型
    config = PipelineConfig(**config_data)
    
    # 执行Pipeline
    results = run_pipeline(config, query="2020年CPI上涨了多少")
    print(json.dumps(results, indent=2, ensure_ascii=False)) 