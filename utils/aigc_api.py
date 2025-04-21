"""
@File   : deepseek_v3.py
@Time   : 2025/02/28 16:55
@Author : yliu.lyndon
@Desc   : None
"""

import json

import requests
from loguru import logger
from openai import OpenAI
from typing import Generator, Optional
import sys

sys.path.append("..")
from services.config import OPENAI_API_KEY


def deepseek_v3_generate(system: str, user: str, **kwargs) -> str:
    """
    """
    # 配置URL
    url = "http://10.10.178.25:12239/aigateway/deepseek/chat/completions"
    # 配置请求头
    headers = {
        "Content-Type": "application/json;charset=utf-8",
    }
    # 配置请求体
    body = {
        "body": {
            "model": "deepseek-chat",
            "maxTokens": kwargs.get("max_tokens", 16384),
            "temperature": kwargs.get("temperature", 0),
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
        },
        "pkey": "MDlGQTM0RUZFOUYxREY5Njk4MzQyQzcwNDQ1MkIxMDY=",
        "source": "Wind.AI.Insight",
    }
    # 发起POST请求
    response = requests.post(url=url, data=json.dumps(body), headers=headers)
    # 处理异常请求
    if response.status_code != 200:
        raise Exception("请求失败!", f"请求状态码: {response.status_code}, 应答数据: {response.text}")
    # 解析应答数据
    response_data = response.json()
    try:
        content = response_data["body"]["choices"][0]["message"]["content"]
        return content
    except Exception as exc:
        if "调用Alice审计服务未通过！" in response_data.get("message", ""):
            raise PermissionError("调用Alice审计服务未通过!", response_data) from exc
        logger.error("请求异常!\n应答数据:\n{}\n异常原因:\n{}", response_data, exc)
        return ""


def deepseek_v3_stream_generate(system: str, user: str, **kwargs) -> str:
    """
    """
    # 配置URL
    url = "http://10.10.178.25:12239/aigateway/deepseek/chat/completions"
    # 配置请求头
    headers = {
        "Content-Type": "application/json;charset=utf-8",
    }
    # 配置请求体
    body = {
        "body": {
            "model": "deepseek-chat",
            "maxTokens": kwargs.get("max_tokens", 16384),
            "temperature": kwargs.get("temperature", 0),
            "stream": True,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
        },
        "pkey": "MDlGQTM0RUZFOUYxREY5Njk4MzQyQzcwNDQ1MkIxMDY=",
        "source": "Wind.AI.Insight",
    }
    # 发起POST请求
    response = requests.post(url=url, data=json.dumps(body), headers=headers, stream=True)
    # 处理异常请求
    if response.status_code != 200:
        raise Exception("请求失败!", f"请求状态码: {response.status_code}, 应答数据: {response.text}")
    # 解析应答数据
    answer_field = "content"
    answer_content = ""
    for line in response.iter_lines(decode_unicode=True):
        line: str
        if not line:
            continue
        elif line.startswith("data: "):
            line = line.lstrip("data: ")
        elif "调用Alice审计服务未通过！" in line:
            raise PermissionError("调用Alice审计服务未通过!", line)
        else:
            pass
        try:
            if line == "[DONE]":
                break
            data_blk = json.loads(line)
            delta = data_blk.get("choices", [{}])[0].get("delta", {})
            if answer_field in delta:
                content = delta.get(answer_field, "")
                answer_content += content
                print(content, end="", flush=True)
        except Exception as exc:
            logger.error("流式处理异常!\n应答数据:\n{}异常原因:\n{}", line, exc)
    return answer_content


def openai_generate(system: str, user: str, **kwargs) -> str:
    """
    使用OpenAI API生成文本回复

    Args:
        system: 系统提示词
        user: 用户输入
        **kwargs: 其他参数
            - model: 模型名称，默认为"gpt-4o-mini"
            - max_tokens: 最大生成token数，默认为4096
            - temperature: 温度参数，控制随机性，默认为0
            
    Returns:
        生成的回复文本
    """
    # 初始化OpenAI客户端
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        # 创建聊天完成请求
        response = client.chat.completions.create(
            model=kwargs.get("model", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0),
            stream=False
        )
        
        # 提取回复内容
        content = response.choices[0].message.content
        return content
        
    except Exception as e:
        logger.error(f"OpenAI API请求异常: {str(e)}")
        return ""


def openai_stream_generate(system: str, user: str, **kwargs) -> str:
    """
    使用OpenAI API流式生成文本回复
    
    Args:
        system: 系统提示词
        user: 用户输入
        **kwargs: 其他参数
            - model: 模型名称，默认为"gpt-4o-mini"
            - max_tokens: 最大生成token数，默认为4096
            - temperature: 温度参数，控制随机性，默认为0
            
    Returns:
        生成的完整回复文本
    """
    # 初始化OpenAI客户端
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        # 创建流式聊天完成请求
        stream = client.chat.completions.create(
            model=kwargs.get("model", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=kwargs.get("max_tokens", 8192),
            temperature=kwargs.get("temperature", 0),
            stream=True
        )
        
        # 处理流式响应
        answer_content = ""
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                answer_content += content
                print(content, end="", flush=True)
        
        return answer_content
        
    except Exception as e:
        logger.error(f"OpenAI流式API请求异常: {str(e)}")
        return ""


if __name__ == '__main__':
    """测试代码"""
    # 测试DeepSeek接口
    # content = stream_generate("", "你是谁？")
    # print("DeepSeek模型回复:", content)
    
    # 测试OpenAI接口
    openai_content = openai_generate("你是一个有用的AI助手。", "中国的首都是哪里？")
    print("OpenAI模型回复:", openai_content)
    
    # # 测试OpenAI流式接口
    # openai_stream_content = openai_stream_generate("你是一个有用的AI助手。", "简要介绍一下北京的历史。")
    # # print("OpenAI流式模型完整回复:", openai_stream_content)
