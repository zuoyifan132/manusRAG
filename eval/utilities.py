# -*- coding: utf-8 -*-
# Created on 2024/8/26
import ast
# -*- coding: utf-8 -*-
# Created on 2024/7/22
import json
import logging
import os
import re
import base64
import random
import time
import numpy as np
import PyPDF2
from datetime import datetime
from typing import List, Union
import openai
import requests
from tqdm import tqdm
import pandas as pd
from tenacity import retry, wait_fixed, stop_after_attempt, RetryError, stop_never
from concurrent.futures import ThreadPoolExecutor, wait

import sys
sys.path.append("..")

from examples.pipeline_example import call_pipeline_service

WAIT_TIME = 5
RETRY_TIMES = 5


def read_excel(path):
    df = pd.read_excel(path)
    # Convert DataFrame to list of lists
    data = df.values.tolist()
    # Remove rows with all NaN values
    cleaned_data = [[x for x in row if not (isinstance(x, float) and np.isnan(x))] for row in data]
    return cleaned_data


def read_file(source_file_name):
    if not os.path.exists(source_file_name):
        logging.warning(f"{source_file_name} file doesn't exists")
    data = []
    with open(source_file_name, 'r', encoding='utf-8') as file:
        for line in tqdm(file, desc="reading files: "):
            json_object = json.loads(line.strip())
            data.append(json_object)

    return data


def read_json(path):
    with open(path, 'r', encoding="utf-8") as file:
        data = json.load(file)
        return data


def valid_res(res, result_pattern=r'"relevance":\s*"([^"]*)"'):
    result_match = re.search(result_pattern, res, re.DOTALL)
    if result_match:
        return result_match.group(1)
    else:
        return None


def extract_tp_fp(data):
    # Updated patterns to handle empty lists as well
    tp_pattern = r'"TP":\s*(\[\s*\{[^]]*\}\s*\]|\[\])'
    fp_pattern = r'"FP":\s*(\[\s*\{[^]]*\}\s*\]|\[\])'
    tp_match = re.search(tp_pattern, data)
    fp_match = re.search(fp_pattern, data)
    tp_result = tp_match.group(1) if tp_match else []
    fp_result = fp_match.group(1) if fp_match else []

    tp_result = ast.literal_eval(tp_result)
    fp_result = ast.literal_eval(fp_result)

    return tp_result, fp_result


def extract_query(text):
    cleaned_string = re.sub(r'```json|```', '', text).strip()
    try:
        json_data = json.loads(cleaned_string)
        return json_data["query"]
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return None


def cosine_similarity(vec_a, vec_b):
    vec_a = np.array(vec_a)
    vec_b = np.array(vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    normalized_a = vec_a / norm_a
    normalized_b = vec_b / norm_b
    cos_sim = np.dot(normalized_a, normalized_b.T)
    return cos_sim


@retry(wait=wait_fixed(10), stop=stop_never)
def text_embedding(text: Union[str, List[str]]) -> Union[None, list[list[float]]]:
    """
    Embed the text provided by bge-m3 text embedding
    @ text: text you want to embed
    """

    def nonempty_checker(text_list):
        for each in text_list:
            if len(each) == 0:
                return False
        return True

    if isinstance(text, list):
        if len(text) == 0:
            logging.warning("text embedding receiving empty list text")
            return None
        if not nonempty_checker(text):
            return [text_embedding(each)[0] for each in text]

    elif isinstance(text, str):
        # handle empty text input
        if len(text) == 0:
            return np.zeros((1, 1024)).tolist()  # this is indeed type list[list[float]]
        text = [text]
    else:
        print("text embedding format doesn't match: ", text)

    params = {"access_token": "",
              "contents": text,
              "model": "bge-m3"}

    URL = "http://10.26.134.33/AISearchBackend/ai-retrieve/text-embedding"

    try:
        resp = requests.post(url=URL, json=params)
        parsed_resp = resp.json()
        embeddings = parsed_resp["embeddings"]  # shape 1 * 1024
    except Exception as e:
        print(f"bad requests: {e}")
        raise

    return embeddings


@retry(wait=wait_fixed(WAIT_TIME), stop=stop_never)
def load_db_batch_embedding(data, single_request_batch_size=16, max_concurrent_requests=3):
    """
    Load and embed data in batches, submitting a specified number of concurrent requests,
    each handling a defined batch size. Waits for all concurrent requests to complete before submitting the next set.

    Args:
    data (list): List of data items to embed.
    single_request_batch_size (int): Number of data items each individual request can handle. max:16
    max_concurrent_requests (int): Maximum number of concurrent requests allowed. max: 3

    Returns:
    np.array: Array of embedded data.
    """
    # Initialize the list to hold all embedded data
    embedded_data = []

    try:
        # Create a ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_concurrent_requests) as executor:
            # Calculate the total number of items processed per full set of concurrent requests
            items_per_full_request_set = single_request_batch_size * max_concurrent_requests

            # Calculate total full sets of requests to be processed
            total_full_sets = len(data) // items_per_full_request_set
            leftover_items = len(data) % items_per_full_request_set

            for set_index in range(total_full_sets + (1 if leftover_items > 0 else 0)):
                # Start index for this set of requests
                start_idx = set_index * items_per_full_request_set
                # End index for this set of requests
                end_idx = min(start_idx + items_per_full_request_set, len(data))

                # Current set of data to process
                current_data_set = data[start_idx:end_idx]
                # List to hold futures for the current set of requests
                futures = []
                for i in range(0, len(current_data_set), single_request_batch_size):
                    try:
                        batch_data = current_data_set[i:i + single_request_batch_size].to_list()
                    except:
                        batch_data = current_data_set[i:i + single_request_batch_size]
                    if len(batch_data) > 0:
                        future = executor.submit(text_embedding, batch_data)
                        futures.append(future)

                # Wait for all futures in the current set to complete before proceeding to the next set
                wait(futures)
                results = [future.result() for future in futures]
                for result in results:
                    embedded_data.extend(result)

                # Print progress
                print(
                    f"\rEmbedding Progress: {set_index + 1}/{total_full_sets + (1 if leftover_items > 0 else 0)} concurrent_batches",
                    end="",
                    flush=True)
    except Exception as e:
        logging.warning(f"Exception during load_db_batch_embedding: {e}")
        raise  # retry

    # Convert list of embeddings to a numpy array with type float32
    db = np.array(embedded_data).astype('float32')
    return db


def deepseek_v3_generation(task, **kwargs):
    """"""
    # 请求URL
    url = "http://10.10.178.25:12239/aigateway/deepseek/chat/completions"
    # 请求头
    headers = {"content-type": "application/json;charset=utf-8"}
    # 请求体
    body = {
        "body": {
            "model": "deepseek-chat",
            "max_tokens": kwargs.get("max_tokens", 8192),
            "temperature": kwargs.get("temperature", 0),
            "top_p": kwargs.get("top_p", 1),
            "top_k": kwargs.get("top_k", 100),
            "stream": kwargs.get("stream", False),
            "messages": [
                {"role": "system", "content": ""},
                {"role": "user", "content": task},
            ],
        },
        "PKey": "MDlGQTM0RUZFOUYxREY5Njk4MzQyQzcwNDQ1MkIxMDY=",
        "source": "Wind.AI.Insight",
    }
    # 发起请求
    response = requests.post(url=url, data=json.dumps(body), headers=headers, stream=kwargs.get("stream", False))
    # 请求失败，提前终止
    if response.status_code != 200:
        logging.error("请求失败!\n请求状态码: {}\n应答数据:\n{}", response.status_code, response.json())
        return ""
    # 解析数据
    response_data = response.json()
    try:
        content = response_data.get("body", {}).get("choices", [])[0].get("message", {}).get("content", "")
        return content
    except Exception as exc:
        logging.error("解析异常!\n应答数据:\n{}\n异常原因:\n{}", response_data, exc)
        return ""
    

def qwen_generation(task):
    """
    Generate text using the Qwen 2.5 model via API call.
    
    Args:
        task (str): The input prompt/task for the language model.
        
    Returns:
        str: The generated text response from the model.
        
    Raises:
        Exception: If the API request fails or returns a non-200 status code.
    """
    # 请求URL
    url = "http://10.100.167.66:11886/v1/chat/completions"
    # 请求头
    headers = {"content-type": "application/json;charset=utf-8"}

    messages = [
        {"role": "system", "content": ""},
        {"role": "user", "content": task}
    ]

    params = {
        "messages": messages,
        "temperature": 0,
        "max_tokens": 12000,
        "top_p": 1,
        "model": "qwen2.5-72b-instruct"
    }

    try:
        resp = requests.post(url=url, json=params, headers=headers)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            error_msg = f"API request failed with status code {resp.status_code}: {resp.text}"
            raise Exception(error_msg)
    except Exception as e:
        raise Exception(f"Error in API call: {str(e)}")
    

def model_generation(task: str, model: str):
    if model == "qwen-max":
        generated_text = qwen_generation(task)
    elif model[:3] == "gpt":
        generated_text = gpt_generation(task, model)
    elif model == "kimi":
        generated_text = kimi_generation(task)
    else:
        raise "Invalid model for generation"

    return generated_text


@retry(wait=wait_fixed(WAIT_TIME), stop=stop_after_attempt(RETRY_TIMES))
def attempt_result_pattern_generation(task, result_pattern, model="gpt-4-turbo"):
    """
        Attempt to generate and validate data that matches the desired format.
        @ task: the type of task that need to be generated using the model API
        @ model: the used model default gpt-4-turbo
    """
    # handling API calling caused error
    try:
        if model[:3] == "gpt":
            generated_text = gpt_generation(task, model)
        else:
            generated_text = qwen_generation(task)
    except Exception as e:
        logging.warning(f"An error occurred during API call: {e}")
        raise  # trigger retry
    # print("generated_text； ", generated_text)
    # handling non-valid data format error
    validate_output = valid_res(generated_text, result_pattern)
    if validate_output is None:
        logging.warning(f"validate_data pattern doesn't match")
        raise  # trigger retry

    return validate_output


def ES_retrieval_api_call(doc_id, doc_type):
    def make_sign():
        t = str(int(time.time() * 1000))
        sign = base64.b64encode(t.encode()).decode()
        return sign

    headers = {
        "Cookie": "JSESSIONID=node01v1bx69f3271a1uo8wdmurf2y88.node0",
        "sign": make_sign(),
    }

    URL = "http://10.10.13.48:8080/MilvusPlatform/dynamic/api/recall"

    params = {
        "docs": doc_id,
        "indexName": "EsRecall",
        "rFields": "extrainfo,title,contents,abstract,publishdate",
        "searchType": doc_type,
        "userId": "11111",
        "sessionId": "11111",
    }

    resp = requests.post(URL, json=params, headers=headers)
    parsed_resp = None

    if resp.status_code == 200:
        try:
            json_response = resp.json()
            result_str = json_response.get("result", [])
            parsed_resp = json.loads(result_str)["hits"]["hits"][0]
        except (ValueError, json.JSONDecodeError) as e:
            raise f" doc_id: {doc_id}, doc_type： {doc_type} parse failed {e}"
    else:
        raise f"Request failed with status code {resp.status_code}"

    if not parsed_resp:
        raise f" doc_id: {doc_id}, doc_type： {doc_type} content empty"

    return parsed_resp


def get_public_date_by_doc_id(doc_id: str):
    ES_news_res = ES_retrieval_api_call(doc_id=doc_id, doc_type="1,2,5")
    ES_reports_res = ES_retrieval_api_call(doc_id=doc_id, doc_type="4")
    ES_bulletin_res = ES_retrieval_api_call(doc_id=doc_id, doc_type="3")
    ES_regulation_res = ES_retrieval_api_call(doc_id=doc_id, doc_type="53")

    has_news_time = ES_news_res.get("_source", None)
    has_reports_time = ES_reports_res.get("_source", None)
    has_bulletin_time = ES_bulletin_res.get("_source", None)
    has_regulation_time = ES_regulation_res.get("_source", None)

    if has_news_time:
        publish_time = has_news_time["publishdate"][0]
        if publish_time:
            return publish_time
        else:
            return None

    elif has_reports_time:
        publish_time = has_reports_time["publishdate"][0]
        if publish_time:
            return publish_time
        else:
            return None

    elif has_bulletin_time:
        publish_time = has_bulletin_time["publishdate"][0]
        if publish_time:
            return publish_time
        else:
            return None

    elif has_regulation_time:
        publish_time = has_regulation_time["publishdate"][0]
        if publish_time:
            return publish_time
        else:
            return None

    else:
        return None


def publish_date_check(doc_id, search_condition_start_time, search_condition_end_time):
    """
        check if the doc_id is in the range of the start and end condition search time
    """
    publish_date = get_public_date_by_doc_id(doc_id)
    publish_date = datetime.strptime(publish_date[:10], "%Y-%m-%d")
    search_condition_start_time = datetime.strptime(search_condition_start_time, "%Y-%m-%d")
    search_condition_end_time = datetime.strptime(search_condition_end_time, "%Y-%m-%d")

    return search_condition_start_time <= publish_date <= search_condition_end_time


def condition_time_correction(query_file_path, ref_file_path, new_ref_save_path):
    """
        correct the original_query_list condition search start and end time
    """
    query_file = read_file(query_file_path)
    ref_file = read_file(ref_file_path)

    new_ref_list = []

    for i in tqdm(range(len(query_file))):
        time.sleep(1)
        search_condition_start_time = query_file[i]["search_condition_start_time"]
        search_condition_end_time = query_file[i]["search_condition_end_time"]

        ref_docs_rel = ref_file[i]["docs_rel"]
        new_ref_docs_rel = []
        query = ref_file[i]["query"]
        for each_docs_rel in ref_docs_rel:
            new_each_docs_rel = []
            for each_doc_rel in each_docs_rel:
                # check if the doc_id is in the range of the start and end condition search time
                correct_time_flag = publish_date_check(each_doc_rel["doc_id"], search_condition_start_time,
                                                       search_condition_end_time)
                # with in the time range
                if correct_time_flag:
                    new_each_docs_rel.append({"doc_id": each_doc_rel["doc_id"]})

            new_ref_docs_rel.append(new_each_docs_rel)

        new_ref_list.append({"query": query, "docs_rel": new_ref_docs_rel})

    # save new ref file
    with open(new_ref_save_path, "w", encoding="utf-8") as file:
        for data in new_ref_list:
            json.dump(data, file, ensure_ascii=False)
            file.write("\n")


def save_data_to_jsonl(data, save_path, mode="w"):
    with open(save_path, mode, encoding="utf-8") as file:
        if isinstance(data, dict):
            json.dump(data, file, ensure_ascii=False)
            file.write("\n")
        elif isinstance(data, list):
            for each_data in data:
                json.dump(each_data, file, ensure_ascii=False)
                file.write("\n")


def parsed_pdf_dir(dir):
    docs = [
        read_pdf(pdf_path)
        for pdf_path in tqdm(get_all_file_paths(dir), "Extracting PDF: ")
    ]
    return docs


def get_all_file_paths(directory):
    """
    Recursively collects all file paths from the given directory.
    :param directory: Path to the directory
    :return: List of file paths
    """
    file_paths = []
    # Walk through all directories and files
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            # Construct the full file path and add it to the list
            file_path = os.path.join(dirpath, filename)
            file_paths.append(file_path)
    return file_paths


def process_dir_json_chunk(dir):
    chunks = []
    for doc_path in tqdm(get_all_file_paths(dir), "Reading chunks: "):
        chunks.extend(read_json_chunk(doc_path))
    return chunks


def process_dir_2_each_doc_json_chunk(dir):
    chunks = []
    for doc_path in tqdm(get_all_file_paths(dir), "Reading chunks: "):
        chunks.append(read_json_source_chunk(doc_path))
    return chunks


def process_dir_2_each_doc_json_summary_chunk(dir):
    chunks = []
    for doc_path in tqdm(get_all_file_paths(dir), "Reading chunks: "):
        chunks.append(read_json_source_summary_chunk(doc_path))
    return chunks


def read_json_chunk(path):
    res = []
    data = read_json(path)
    for json_ojb in data:
        res.append([json_ojb["chunk"]])

    return res


def read_json_source_chunk(path):
    res = []
    data = read_json(path)
    source = data[0]["source"][:-4]
    for json_ojb in data:
        res.append(json_ojb["chunk"])

    return [source, res]


def read_json_source_summary_chunk(path):
    res = []
    data = read_json(path)
    source = data[0]["source"][:-4]
    for json_ojb in data:
        res.append({
            "chunk": json_ojb["chunk"],
            "chunk_type": "summary_node" if json_ojb.get("chunk_number", None) is not None else "leaf_node"
        })

    return [source, res]


def read_pdf(image_path):
    paper = ""
    # Open the PDF file
    with open(image_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        # Iterate over each page and extract text
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text = page.extract_text()
            paper = paper + " " + text
    return [image_path, paper]


def attempt_call_chunk_split_api(
    text,
    min_chunk_size,
    max_chunk_size,
    url='http://10.100.2.195:7800/ai-retrieve/test/chunk/split/text'
):
    response, parsed_resp = None, None

    # JSON request header, content should be in json format
    headers = {
        'Content-Type': 'application/json'
    }
    # specific request params

    payload = {
        'text': text,
        'min_chunk_size': min_chunk_size,
        'max_chunk_size': max_chunk_size
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        parsed_resp = response.json()
    except Exception as e:
        response.raise_for_status()
    # print("parsed_resp: ", parsed_resp)
    # chunks = [chunk["content"] for chunk in parsed_resp]

    return parsed_resp


def group_question(question):
    # Convert the data into a pandas DataFrame
    df = pd.DataFrame(question, columns=['Title', 'Question'])
    # Group the data by 'Title' and aggregate questions under each title, then convert to dictionary
    grouped_dict = df.groupby('Title')['Question'].apply(list).to_dict()
    return grouped_dict


def random_double_index_generator(chunk_len):
    random_indices = random.sample(range(chunk_len), 2)
    return random_indices


def get_chunk_based_on_mode(mode: str, naive_pdf_path: str, treeRAG_chunk_path: str):
    doc_chunks = []

    if mode == "naive":
        # prepare data for naiveRAG
        PDF_data = parsed_pdf_dir(naive_pdf_path)
        for source, doc in tqdm(PDF_data, desc="chunking: "):
            res = attempt_call_chunk_split_api(doc, 100, 200)
            doc_chunks.append([
                source.split("\\")[-1][:-4],
                [
                    each["content"]
                    for each in res
                ]
            ])
    elif mode == "tree":
        # prepare data for TreeRAG
        doc_chunks = process_dir_2_each_doc_json_chunk(treeRAG_chunk_path)
    else:
        raise f"Invalid mode {mode}"

    return doc_chunks


def get_ground_truth(working_dir: str, d_source: str, q: str):
    labels = read_json(f"{working_dir}\\{d_source}-label.json")
    ground_truth = labels[q]

    return ground_truth


def print_and_save_metrics(
        total_hit: int,
        count: int,
        total_recall: float,
        experiment_details: str,
        save_metric_path: str,
        **kwargs,
):
    # Calculate hit rate and recall
    hit_rate = total_hit / count if count != 0 else 0
    recall = total_recall / count if count != 0 else 0

    # Log the current date and time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    metrics = ""
    # Add any additional keyword arguments to the metrics string
    for key, value in kwargs.items():
        metrics += f"{key}: {value}\n"

    # Prepare the metrics string
    metrics += (
        f"Experiment Details: {experiment_details}\n"
        f"Date: {current_time}\n"
        f"Hit Rate: {hit_rate:.4f}\n"
        f"Recall: {recall:.4f}\n"
        f"Count: {count}\n\n"
    )

    print("metrics: ", metrics)

    # Read the current contents of the file
    try:
        with open(save_metric_path, 'r', encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        # If the file does not exist, initialize it with empty content
        content = ""
    # Check if the required delimiters are present
    if "singleDocFalshRAG:" not in content:
        content += "singleDocFalshRAG:\n\n"
    # Append the metrics under the correct section
    content = content.replace("singleDocFalshRAG:\n\n", f"singleDocFalshRAG:\n\n{metrics}", 1)

    # Write the updated content back to the file
    try:
        with open(save_metric_path, 'w', encoding="utf-8") as file:
            file.write(content)
        print(f"Metrics successfully saved to {save_metric_path}")
    except Exception as e:
        print(f"Failed to save metrics to file: {e}")


def group_questions_by_doc(data):
    grouped_data = {}

    DOC_NAME_PATH_MAPIING = {
        "年报2022东阿阿胶": "/mnt/storage/yfzuo/flashC_project/rag/eval/eval_data/test_reports/年报2022东阿阿胶.pdf",
        "年报2022中国卫通": "/mnt/storage/yfzuo/flashC_project/rag/eval/eval_data/test_reports/年报2022中国卫通.pdf",
        "年报2022京沪高铁": "/mnt/storage/yfzuo/flashC_project/rag/eval/eval_data/test_reports/年报2022京沪高铁.pdf",
        "年报2022分众传媒": "/mnt/storage/yfzuo/flashC_project/rag/eval/eval_data/test_reports/年报2022分众传媒.pdf",
        "年报2022南凌科技": "/mnt/storage/yfzuo/flashC_project/rag/eval/eval_data/test_reports/年报2022南凌科技.pdf",
        "年报2022国投资本": "/mnt/storage/yfzuo/flashC_project/rag/eval/eval_data/test_reports/年报2022国投资本.pdf",
        "年报2022牧原股份": "/mnt/storage/yfzuo/flashC_project/rag/eval/eval_data/test_reports/年报2022牧原股份.pdf",
        "年报2022申能股份": "/mnt/storage/yfzuo/flashC_project/rag/eval/eval_data/test_reports/年报2022申能股份.pdf",
        "年报2022荣安地产": "/mnt/storage/yfzuo/flashC_project/rag/eval/eval_data/test_reports/年报2022荣安地产.pdf"
    }

    for row in data:
        if row:  # Check if the row is not empty
            doc_name = row[0]
            # If doc_name is not already in the dictionary, initialize it with an empty list
            if doc_name not in grouped_data:
                grouped_data[doc_name] = {"chunks": [], "pdf_path": ""}
            # Append the question (and other relevant information) to the list for this doc_name
            grouped_data[doc_name]["chunks"].append(row[1:])
            grouped_data[doc_name]["pdf_path"] = DOC_NAME_PATH_MAPIING[doc_name]

    return grouped_data


def flash_rag_ingest(pdf_path, collection_name):
    config = {
        "doc_2_text": {
            "strategy": {"pdf": "pypdf2"},
            "doc_path": ""
        },
        "chunk_text": [
            {
                "file_type": "pdf",
                "strategy": "recursive",
                "params": {
                    "format_chunk_flag": True
                }
            }
        ],
        "ingest_text": [
            {
                "type": "milvus",
                "params": {
                    "batch_size_limit": 16,
                    "collection_name": ""
                }
            }
        ],
        "base_url": "http://10.106.51.224:17724"
    }

    # specify the pdf path and collection name
    config["doc_2_text"]["doc_path"] = pdf_path
    config["ingest_text"][0]["params"]["collection_name"] = collection_name

    print("Using params to ingest: ", json.dumps(config, indent=4, ensure_ascii=False))

    # call the rag service
    res = call_pipeline_service(config_file=config)
    return res


def flash_rag_search(query, top_k, collection_name):
    config = {
        "retrieval": [
            {
                "type": "milvus",
                "params":{
                    "top_k": top_k,
                    "collection_name": collection_name,
                }
            }
        ],
        "base_url": "http://10.106.51.224:17724"
    }

    # call the rag service
    res = call_pipeline_service(config_file=config, query=query)
    return res


if __name__ == "__main__":
    # res = flash_rag_ingest(
    #     pdf_path="/mnt/storage/yfzuo/flashC_project/rag/eval/eval_data/test_reports/年报2022东阿阿胶.pdf",
    #     collection_name="dongeejiao_test_collection"
    # )
    # print("res: ", res)

    # print(flash_rag_search(
    #     query="miner原理是什么呢，注重于浏览器的什么？",
    #     top_k=5,
    #     collection_name="nianbao2022dongeejiao_rag_eval_collection"
    # ))

    print(qwen_generation("你叫什么"))
