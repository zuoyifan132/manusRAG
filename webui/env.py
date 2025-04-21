"""
@File   : env.py
@Time   : 2024/07/31 18:00
@Author : Wind.FlashC
@Desc   : 获取基础环境配置.
"""

import os

import yaml

# 项目目录
BASE_DIR = os.path.dirname(__file__)
# 存储目录
STORAGE_DIR = ""
# 运行环境
ENV = ""


def _load_base_config(base_dir: str) -> None:
    """
    加载项目基础配置.

    :param base_dir: 项目目录.
    """
    global ENV, BASE_DIR, STORAGE_DIR

    _optional_env = {"local", "dev", "test", "prod-sh", "prod-nj", "prod-nj-proc", "aispace", }

    base_config_file = os.path.join(base_dir, "config", "config.yaml")
    with open(base_config_file, "r", encoding="utf-8") as fp:
        base_config = yaml.load(fp, Loader=yaml.FullLoader)

    ENV = base_config.get("env")
    if not ENV or ENV not in _optional_env:
        raise EnvironmentError("运行环境错误", f"没有指定运行环境, 可选运行环境为: {_optional_env}.")

    if ENV == "aispace":
        STORAGE_DIR = "/wind/aispace/train/service_files"
    else:
        STORAGE_DIR = BASE_DIR


_load_base_config(BASE_DIR)
