"""
@File   : expo_util.py
@Time   : 2024/09/29 13:28
@Author : Wind.FlashC
@Desc   : None
"""

from typing import Any, List

# from expoclient import AppServer, CommandHeader, IAsyncRequestCallback
from loguru import logger

# from utils.config_util import get_expo_config, get_log_config


class AsyncCallback():
    """
    Expo异步回调模块.
    """

    def async_callback(self, command_header: str, result_object_list: List, user_object, is_success: bool, error_info: str):
        """
        异步回调.

        :param command_header: 响应消息的头信息
        :param result_object_list: 响应结果
        :param user_object: 用户自己的对象
        :param is_success: 请求是否成功
        :param error_info: 如果失败，对应的错误信息
        :return:
        """
        if is_success:
            command_id = command_header.command_id
            result = result_object_list[0]
            result_type = type(result)
            logger.info("Expo调用成功.\ncommand_id: {},\nresult_type: {},\nresult: {}", command_id, result_type, result)
        else:
            logger.error("Expo调用失败.\n{}", error_info)


class ExpoClient:
    """
    Expo客户端模块.
    """
    __name__ = "expo_client"

    def __init__(self, app_class: int, command_id: int, user_id: int = 0, request_mode: str = "sync", timeout: int = 60) -> None:
        """初始化.

        :param app_class: AppClass.
        :param command_id: CommandID.
        :param request_mode: 请求方式.
        :param timeout: 请求超时时长, 单位为秒.
        """
        if request_mode == "sync":
            # 如果需要发送同步消息, is_send_async_message必须为False
            is_send_async_message = False
        elif request_mode == "async":
            # 如果需要发送异步消息, is_send_async_message必须为True, 并且创建异步回调模块
            is_send_async_message = True
            # self.async_callback = AsyncCallback()
        else:
            raise ValueError("参数`request_mode`仅支持'sync'或者'async'!")
        # 请求超时时长设置
        self.timeout = timeout * 1000
        # 创建Expo消息的header信息
        self.command_header = CommandHeader(app_class, command_id, user_id)
        # 创建Expo服务
        self.app_server = self.get_app_server(is_send_async_message)
        # 获取发送消息的的代理
        self.proxy = self.app_server.get_proxy()

    def __enter__(self):
        self.app_server.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.app_server.stop()

    def get_app_server(self, is_send_async_message: bool = False):
        pass

    def start(self) -> None:
        """
        启动服务.
        """
        self.app_server.start()

    def stop(self) -> None:
        """
        停止服务.
        """
        self.app_server.stop()

    def sync_send(self, data: List[Any]) -> Any:
        """
        同步发送.

        :param data: 请求数据.
        :return: 应答数据.
        """
        result = self.proxy.do_sync_command(self.command_header, data, self.timeout)
        return result

    def async_send(self, data: List[Any]) -> Any:
        """
        异步发送.

        :param data: 请求数据.
        :return: 应答数据.
        """
        async_callback = AsyncCallback()
        flag, msg = self.proxy.do_async_command(self.command_header, data, async_callback, None, self.timeout)
        if flag:
            logger.info("发送异步消息成功.")
        else:
            logger.error("发送异步消息失败.\n{}", msg)
        return
