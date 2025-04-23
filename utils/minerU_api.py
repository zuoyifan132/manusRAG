"""
@File   : mineru_file_parse.py
@Time   : 2025/03/11 16:30
@Author : yfzuo
@Desc   : MinerU 文件解析API调用
"""
import sys
import json
from typing import Optional, Dict
import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.append("..")

from parser.config import REQUEST_TIMEOUT, MAX_RETRIES
from services.config import MINERU_API_URL


# @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
def mineru_file_parse_api(file_path: str) -> Optional[Dict]:
    """
    调用MinerU文件解析API解析PDF文件
    
    Args:
        file_path: 文件路径
        additional_params: 附加参数字典，可选
        
    Returns:
        返回的JSON数据字典，如果请求失败则返回None
    """
    if not file_path or not isinstance(file_path, str):
        logger.error("文件路径无效")
        return None
    
    try:
        with open(file_path, "rb") as file:
            files = {"file": file}
            
            response = requests.post(
                url=MINERU_API_URL,
                files=files,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.error(f"API请求失败: {response.status_code}\n响应数据: {response.text}")
                return None
            
            response_data = response.json()
            return response_data
    except FileNotFoundError:
        logger.error(f"文件未找到: {file_path}")
        return None
    except requests.exceptions.Timeout:
        logger.error("API请求超时")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"API请求异常: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"处理响应时发生错误: {str(e)}")
        return None


if __name__ == "__main__":
    # 测试代码
    test_file_path = "../test/dummy_file/rag_and_broswer_use.pdf"
    result = mineru_file_parse_api(file_path=test_file_path)
    if result:
        print(f"API调用成功，返回结果:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print("API调用失败")
