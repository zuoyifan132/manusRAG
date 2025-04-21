"""
@File   : gpt_4o.py
@Time   : 2025/03/20 11:39
@Author : Wind.FlashC
@Desc   : None
"""

import json

import requests
from loguru import logger


class LLMCaller(object):
    def __init__(self, api_key, **kwargs):
        self.api_key = kwargs.get('api_key', None)
        self.base_url = kwargs.get('base_url', None)
        self.model = kwargs.get('model', 'deepseek-chat')
        self.inited = False
        self._init()

    def _init(self):
        if not self.inited:
            pass
        self.inited = True

    # 流式生成函数

    def chat_stream(self, messages, **kwargs):
        """Stream text generation from the custom API"""
        # 配置URL
        url = "http://10.10.178.25:12239/aigateway/deepseek/chat/completions"
        # 配置请求头
        headers = {
            "Content-Type": "application/json;charset=utf-8"
        }
        # 配置请求体
        body = {
            "body": {
                "model": self.model,
                "maxTokens": kwargs.get("max_tokens", 16384),
                "temperature": kwargs.get("temperature", 0),
                "stream": True,
                "messages": messages,
            },
            "pkey": "MDlGQTM0RUZFOUYxREY5Njk4MzQyQzcwNDQ1MkIxMDY=",
            "source": "Wind.AI.Insight",
        }

        # 发起POST请求
        response = requests.post(url=url, data=json.dumps(body), headers=headers, stream=True)

        # 处理异常请求
        if response.status_code != 200:
            raise Exception(f"请求失败! 请求状态码: {response.status_code}, 应答数据: {response.text}")

        # 流式处理响应
        answer_field = "content"
        answer_content = ""

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            elif line.startswith("data: "):
                line = line.lstrip("data: ")
            elif "调用Alice审计服务未通过！" in line:
                raise PermissionError("调用Alice审计服务未通过!", line)

            try:
                if line == "[DONE]":
                    break
                data_blk = json.loads(line)
                delta = data_blk.get("choices", [{}])[0].get("delta", {})
                if answer_field in delta:
                    content = delta.get(answer_field, "")
                    answer_content += content
                    yield content
            except Exception as exc:
                logger.error(f"流式处理异常!\n应答数据:\n{line}\n异常原因:\n{exc}")

        return answer_content


if __name__ == '__main__':
    """"""
    caller = LLMCaller('')
    content = caller.chat_stream(messages=[{"role": 'user', 'content': 'who are you'}])
    print("模型回复:", content)
