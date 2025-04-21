"""
@File   : tool_util.py
@Time   : 2025/04/15 08:59
@Author : Wind.FlashC
@Desc   : None
"""

import json
from typing import ByteString, Callable

import pandas as pd

from utils.expo_util import ExpoClient

# 工具描述 >>> 基于WindDPU的查询
wind_dpu_searcher = {
    "name": "wind_dpu_searcher",
    "description": "这是基于的Wind数据库的查询工具。根据传入的用户问题来查询市场数据、企业数据、宏观经济等数据",
    "parameters": {
        "query": {
            "description": """用户问题""",
            "type": "str"
        }
    },
    "return": {
        "output": {
            "description": "查询到的数据",
            "type": "str"
        }
    }
}


# 工具描述 >>> 基于WindRAG的查询
wind_rag_searcher = {
    "name": "wind_rag_searcher",
    "description": "这是基于RAG的Wind数据库的查询工具。根据传入的用户问题来获取公告、研报、新闻等内容",
    "parameters": {
        "query": {
            "description": """用户问题""",
            "type": "str"
        }
    },
    "return": {
        "output": {
            "description": "查询到的数据",
            "type": "str"
        }
    }
}


# 工具描述 >>> 计算器
calculator = {
    "name": "calculator",
    "description": "这是一个计算器，输入计算表达式，返回计算结果",
    "parameters": {
        "expression": {
            "description": """计算表达式，如3+2""",
            "type": "str"
        }
    },
    "return": {
        "output": {
            "description": "计算结果，1代表成功，0代表失败",
            "type": "float"
        }
    }
}


def search_by_wind_dpu(query: str) -> str:
    """
    基于Wind的DPU服务的查询.
    
    :param query: 问题.
    :return: 答案.
    """
    __tool_name__ = "wind_dpu_searcher"
    # Expo接口配置
    app_class = 2096
    command_id = 28904
    # 请求参数配置
    input_args = {
        "question": query,
        "requestApp": "Wind.AI.Insight",
    }
    # 请求数据
    request_data = [json.dumps(input_args)]

    try:
        # 请求Expo接口, 获得应答数据
        with ExpoClient(app_class, command_id, request_mode="sync") as expo_client:
            response: list[ByteString] | None = expo_client.sync_send(request_data)
            # 异常情况, 请求失败
            if response is None:
                return f"工具-{__tool_name__}: 执行失败!"
            response_data: dict = json.loads(response[0])
            # 异常情况, 直接返回应答数据
            # 1. 请求状态不为200
            if response_data["State"] != "200":
                return f"工具-{__tool_name__}: {response_data['Msg']}!"
            # 解析表格
            tables = []
            for _, table_info in response_data.get("Query", {}).items():
                try:
                    table = _parse_table(table_info)
                except ImportError as err:
                    raise err
                except:
                    table = ""
                if table:
                    tables.append(table)
            # 工具执行返回
            if not tables:
                # 没有查询到表格, 返回提示
                return f"工具-{__tool_name__}: 没有查询到数据!"
            else:
                # 查询到表格, 返回表格数据
                return f"工具-{__tool_name__}: 查询的数据如下:\n" + "\n\n".join(tables)
    except Exception as exc:
        return f"工具-{__tool_name__}: 执行失败! 异常原因: {exc}"
    

def _parse_table(table_info: dict) -> str:
    """
    表格解析.

    :param table_info: 表格信息表述字典.
    :return: Markdown格式的表格.
    """
    # 解析表头字段名称
    table_field_names = [dic["Name"] for dic in table_info["Headers"]]
    # 解析表头字段类型
    table_field_dtypes = [dic["DataType"] for dic in table_info["Headers"]]
    # 解析表格数据
    table_data = []
    for rows in table_info["Content"]:
        _row_data = []
        for i, item in enumerate(rows):
            try:
                if table_field_dtypes[i] == "composite" or "Label" in item:
                    _row_data.append(eval(item)["Label"])
                else:
                    _row_data.append(item)
            except:
                _row_data.append("-")
        table_data.append(_row_data)
    # 生成表格
    df = pd.DataFrame(table_data, columns=table_field_names)
    # 返回Markdown格式的表格
    res_df = df.to_markdown()
    return res_df


def search_by_wind_rag(query: str) -> str:
    """
    基于Wind的RAG服务的查询.
    
    :param query: 问题.
    :return: 答案.
    """
    __tool_name__ = "wind_rag_searcher"
    # Expo接口配置
    app_class = 2296
    command_id = 2354
    # 请求参数配置
    input_args = {
        "serviceName": "ComprehensiveQuery",
        "userId": 6351684,
        "source": "Wind.AI.Insight",
        "query": query,
        "docType": "1,2",
        "topK": 15,
    }
    # 请求数据
    request_data = [json.dumps(input_args)]
    try:
        # 请求RAG的Expo接口, 根据问句查询Wind数据库
        with ExpoClient(app_class, command_id, request_mode="sync") as expo_client:
            # 发送请求数据, 获得应答数据
            response: list[ByteString] | None = expo_client.sync_send(request_data)
            # 异常情况, 请求失败, 无应答数据
            if response is None:
                return f"工具-{__tool_name__}: 执行失败!"
            # 请求成功, 解析应答数据
            response_data: dict = json.loads(response[0])
            # 异常情况, 直接返回应答数据
            # 1. 请求状态不为0
            if response_data["status"] != "0":
                return f"工具-{__tool_name__}: {response_data['message']}!"
            # 解析文档
            docs = []
            doc_info_list = eval(response_data["result"])
            for doc_info in doc_info_list:
                try:
                    doc = _parse_document(doc_info)
                except:
                    doc = ""
                if doc:
                    docs.append(doc)
            # 工具执行返回
            if not docs:
                # 没有查询到文档, 返回提示
                return f"工具-{__tool_name__}: 没有查询到数据!"
            else:
                # 查询到文档, 返回文档数据
                return f"工具-{__tool_name__}: 查询的数据如下:\n" + "\n\n".join(docs)
    except Exception as exc:
        return f"工具-{__tool_name__}: 执行失败!"
    

def _parse_document(doc_info: dict) -> str:
    """
    文档解析.

    :param table_info: 文档信息表述字典.
    :return: 文档内容.
    """
    doc = doc_info.get("content", "")
    return str(doc)


def calculate(expression: str) -> str:
    """
    使用计算器计算表达式.

    :param expression: 表达式.
    :return: 计算结果.
    """
    try:
        result = eval(expression)
        return str(result)
    except:
        return "工具执行失败!"


# 工具描述
TOOLS_DESC = [
    wind_dpu_searcher,
    # wind_rag_searcher,
    calculator,
]

# 工具
TOOLS: dict[str, Callable] = {
    "wind_dpu_searcher": search_by_wind_dpu,
    # "wind_rag_searcher": search_by_wind_rag,
    "calculator": calculate,
}
