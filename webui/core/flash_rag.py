"""
@File   : flash_rag.py
@Time   : 2025/04/14 19:08
@Author : yliu.lyndon
@Desc   : Flash RAG 知识库检索系统核心功能
"""

import sys
print(sys.path)

import json
from loguru import logger
import requests
import os
from typing import Dict, Any, List, Union, Optional
from webui.utils.aigc_api import openai_stream_generate
from pymilvus import MilvusClient
from database.milvus.config import LOCAL_MILVUS_LITE_DB_PATH, MILVUS_URI


def ingest_data(file_path: str = "", config: str = None):
    """
    处理上传的文件并将其添加到知识库中
    
    Args:
        files: 上传的文件列表
        config: 配置文件路径
    
    Returns:
        dict: 操作结果信息
    """
    # 加载配置文件
    try:
        with open(config, "r") as f:
            config_data = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"读取配置文件失败: {str(e)}"}
    
    # 如果同时提供了文件和配置，则上传的文件会覆盖配置中的doc_path
    if file_path and len(file_path) > 0:        
        # 如果配置中存在doc_2_text，则覆盖其doc_path
        if "doc_2_text" in config_data:
            config_data["doc_2_text"]["doc_path"] = file_path
            print(f"文件路径已更新为: {file_path}")

        print(f"using config_data to ingest data: {config_data}")
        
        # 使用修改后的配置调用服务
        return call_pipeline_service(config_data, "")
    else:
        # 如果只有配置文件，直接使用配置文件调用服务
        return call_pipeline_service(config, "")


def search_data(query: str, config: str = None):
    """
    根据查询检索知识库中的相关信息
    
    Args:
        query (str): 用户查询
        config (str): 配置文件路径
    
    Returns:
        list: 检索结果列表
    """
    # 加载配置文件
    try:
        with open(config, "r") as f:
            config_data = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"读取配置文件失败: {str(e)}"}

    result = call_pipeline_service(config_data, query)

    print(f"search_data result: {result}")
        
    # 如果执行成功，转换结果格式
    if result.get("status") == "success":
        if "reranked_results" in result:
            search_results = result.get("reranked_results", [])
        else:
            search_results = result.get("search_results", [])[:10]
        
        # 转换为前端需要的格式
        formatted_results = []
        for item in search_results:
            # 将Milvus Manager格式转换为前端需要的格式
            formatted_item = {
                "文档": item.get("metadata", {}).get("title", "未知文档"),
                "相关度": item.get("score", 0),
                "内容": item.get("chunk", "无内容")
            }
            formatted_results.append(formatted_item)

        return formatted_results
    else:
        return []


def get_milvus_status(use_milvus_lite: bool = True) -> dict:
    """
    获取Milvus数据库的状态，包括最近更新时间
    
    Args:
        use_milvus_lite (bool): 是否使用MilvusLite，默认为True
    
    Returns:
        dict: 包含Milvus数据库状态信息的字典
    """
    try:
        # 根据use_milvus_lite选择客户端
        client = MilvusClient(
            uri=LOCAL_MILVUS_LITE_DB_PATH if use_milvus_lite else MILVUS_URI,
            token="root:Milvus" if not use_milvus_lite else None
        )

        collections = client.list_collections()
        collections_info = []
        total_entities = 0

        for collection_name in collections:
            try:
                stats = client.get_collection_stats(collection_name=collection_name)
                schema = client.describe_collection(collection_name=collection_name)

                # 提取实体数量
                row_count = int(stats.get("row_count", 0))
                total_entities += row_count

                # 检查索引状态 - 更严格的检查
                index_infos = stats.get("index_infos", [])
                index_status = "已建立" if index_infos and len(index_infos) > 0 else "未建立"

                # 尝试获取最近更新时间
                last_update = schema.get("last_modified_time", None)
                if not last_update:
                    # 如果没有 last_modified_time，尝试从数据中获取
                    try:
                        client.load_collection(collection_name)
                        result = client.query(
                            collection_name=collection_name,
                            filter="",
                            output_fields=["timestamp"],
                            limit=1,
                            sort_field="timestamp",
                            sort_order="desc"
                        )
                        # 增加对结果的健壮性检查
                        last_update = str(result[0]["timestamp"]) if result and len(result) > 0 and "timestamp" in result[0] else schema.get("create_time", "未知")
                    except Exception as query_err:
                        logger.warning(f"查询集合 {collection_name} 时间戳失败: {str(query_err)}")
                        last_update = schema.get("create_time", "未知")

                collections_info.append({
                    "name": collection_name,
                    "row_count": row_count,
                    "index_status": index_status,
                    "create_time": schema.get("create_time", "未知"),
                    "last_update": last_update
                })
            except Exception as e:
                logger.error(f"获取集合 {collection_name} 信息失败: {str(e)}")
                collections_info.append({
                    "name": collection_name,
                    "row_count": 0,
                    "index_status": "获取失败",
                    "create_time": "未知",
                    "last_update": "未知"
                })

        return {
            "status": "ok",
            "collections": collections,
            "collections_info": collections_info,
            "total_entities": total_entities,
            "collection_count": len(collections)
        }
    except Exception as e:
        logger.error(f"获取Milvus状态失败: {str(e)}")
        return {"status": "error", "collections": [], "collections_info": [], "total_entities": 0, "collection_count": 0}


def call_pipeline_service(
        config_file: Union[str, Dict], 
        query: str = "", 
    ) -> Dict[str, Any]:
    """调用Pipeline服务，支持同时上传配置和文件"""
    # 加载配置文件
    if isinstance(config_file, str):
        with open(config_file, "r") as f:
            config = json.load(f)
    elif isinstance(config_file, Dict):
        config = config_file
    else:
        raise ValueError(f"input invalid config_file type: {type(config_file)}")

    base_url = config["base_url"]
    url = f"{base_url}/pipeline"
    
    # 准备请求数据
    request_data = {"data": json.dumps({"config": config, "query": query})}

    # check if the file path is provided in the config
    if config.get("doc_2_text", None) is not None:
        doc_path = config.get("doc_2_text", None).get("doc_path", "")
        
        if not doc_path:
            raise ValueError("Your provided doc_2_text doc_path is not valid")
        else:
            if doc_path and os.path.exists(doc_path):
                file_name = os.path.basename(doc_path)
                file_type = file_name.split(".")[-1].lower()
                
                with open(doc_path, "rb") as f:
                    files = {"file": (f.name, f, f"application/{file_type}")}
                    response = requests.post(url, files=files, data=request_data, timeout=1080000)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        print(f"错误: {response.status_code}")
                        print(response.text)
                        return {"status": "error", "message": f"HTTP错误: {response.status_code}"}
    # search pipeline
    else:
        response = requests.post(url, data=request_data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"错误: {response.status_code}")
            print(response.text)
            return {"status": "error", "message": f"HTTP错误: {response.status_code}"}
        

def aigc_answer(query: str, context: str, config: str = None, stream=True):
    """
    使用AIGC模型生成回答
    
    Args:
        query (str): 用户查询
        context (str): 检索到的相关上下文
        config (str): 配置文件路径
        stream (bool): 是否使用流式生成
    
    Returns:
        生成器，每次yield一个token
    """
    # 构造系统提示词
    system_prompt = (
        f"(根据以下检索到的相关信息，生成简洁且准确的回答：\n"
        f"请以专业且清晰的语言回答，突出关键点，不加入额外内容。)"
        f"请注意回答要换航，注意排版"
        f"请将你回答中所用到的信息在Reference区域进行注明,要求追加文档的原文"
        f"请注意所给的文档是结构化的数据：e.g.: markdown # ## etc"
        f"相关信息：{context}\n"
        f"问题：{query}\n"
    )

    logger.info(f"system_prompt: {system_prompt}")
    
    # 配置参数
    model = "gpt-4o-mini"  # 默认模型
    temperature = 0.0      # 默认温度
    
    # 如果有配置文件，加载配置
    if config:
        try:
            with open(config, "r") as f:
                config_data = json.load(f)
                if "aigc" in config_data:
                    aigc_config = config_data["aigc"]
                    if "model" in aigc_config:
                        model = aigc_config["model"]
                    if "temperature" in aigc_config:
                        temperature = float(aigc_config["temperature"])
        except Exception as e:
            logger.warning(f"读取AIGC配置失败: {str(e)}")
    
    # 使用流式API生成回答，直接返回生成器
    token_generator = openai_stream_generate(
        system=system_prompt, 
        user=query,
        model=model,
        temperature=temperature
    )
    
    # 返回生成器
    return token_generator
