"""
@File   : config_util.py
@Time   : 2025/02/20 19:47
@Author : Wind.FlashC
@Desc   : 获取项目配置信息.
"""

import os
from typing import Any, Dict

import yaml

from env import BASE_DIR, ENV

# 项目配置信息
CONFIG = {}
# 配置加载标志
LOADED = False


def get_config(section_name: str = None) -> Dict:
    """
    根据章节名称获取配置信息.

    :param section_name: 章节名称. 如果为`None`, 则获取所有的配置信息.
    :return: 返回`section_name`的配置信息. 如果`section_name`为`None`, 则返回所有的配置信息.
    """
    if section_name is None:
        global CONFIG
        return CONFIG
    else:
        return _config(section_name)


def get_expo_config(category: str) -> Dict:
    """
    获得WindExpo相关配置信息.

    :param category: Expo客户端类型. 仅支持"client"或者"server".
    :return: WindExpo相关配置信息.
    """
    return _config("expo", category)


def get_uvicorn_config() -> Dict:
    """
    获得外部服务uvicorn http相关配置信息.

    :return: 返回外部服务uvicorn http相关配置信息.
    """
    return _config("server", "http", "uvicorn")


def get_log_config(log_name: str) -> Dict:
    """"
    获得日志相关配置信息.

    :return: 返回日志相关配置信息.
    """
    return _config("log", log_name)


def _check() -> None:
    """
    检查是否加载过配置文件.
    """
    global LOADED
    if not LOADED:
        raise RuntimeError("配置文件未被加载, 请执行: `_load_app_config(base_dir, env)`.")


def _config(*args) -> Any:
    """
    从所有配置中按照层级读取配置信息.

    :param args: 层级数组, 会逐层的读取.
    :return: 返回最后一层的配置信息.
    """
    global CONFIG
    _check()
    root = CONFIG
    for arg in args:
        root = root.get(arg)
    return root


def _load_config(base_dir: str, env_name: str) -> None:
    """
    加载项目配置.

    :param base_dir: 项目基础目录.
    :param env_name: 运行环境名称.
    """
    global CONFIG, LOADED
    config_file_path = os.path.join(base_dir, "config", "config-" + env_name + ".yaml")
    with open(config_file_path, "r", encoding="utf-8") as fp:
        CONFIG = yaml.load(fp, Loader=yaml.FullLoader)
    LOADED = True


_load_config(BASE_DIR, ENV)
