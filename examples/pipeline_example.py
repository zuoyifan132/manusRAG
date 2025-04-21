import json
import requests
import argparse
import os
from typing import Optional, Dict, Any, Union

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


def print_results(result: Dict[str, Any], query: str) -> None:
    """打印结果"""
    if not result:
        print("没有获取到结果")
        return
        
    print("\n=== Pipeline执行结果 ===")
    
    # 打印执行状态
    status = result.get("status", "未知")
    print(f"执行状态: {status}")
    
    if status != "success":
        reason = result.get("reason", "未知原因")
        print(f"失败原因: {reason}")
        return
    
    print("result: ", json.dumps(result, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="调用Pipeline服务示例")
    parser.add_argument("--config", type=str, default="examples/search_example_config.json", help="配置文件路径")
    parser.add_argument("--query", type=str, default="2020年CPI上涨了多少", help="查询问题")
    
    args = parser.parse_args()
    
    # 输出配置信息
    print(f"\n=== 配置信息 ===")
    print(f"配置文件: {args.config}")
    print(f"查询问题: {args.query}")
    
    # 调用服务
    print("\n正在调用Pipeline服务...")
    result = call_pipeline_service(args.config, args.query)
    
    # 打印结果
    print_results(result, args.query) 