"""
@File   : agent.py
@Time   : 2025/04/14 19:08
@Author : yliu.lyndon
@Desc   : None
"""

import requests
from loguru import logger


class FlashAgentPlanner:
    """"""

    def __init__(self) -> None:
        """"""
        self.url = "http://10.106.51.224:18888/plan"

    def plan(self, data: dict) -> dict:
        """"""
        # 发送 POST 请求
        response = requests.post(self.url, json=data)
        #
        if response.status_code != 200:
            logger.error("服务异常!\n模型返回:\n{}", response.text)
            raise Exception("服务异常!")
        response_data = response.json()
        try:
            return response_data["output"]
        except Exception as exc:
            logger.error("解析异常!\n模型返回:\n{}", response_data)
            raise Exception(f"解析异常!, 异常原因: {exc}")
