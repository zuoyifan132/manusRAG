import json
import uuid
import os
import sys
import time
from loguru import logger
from typing import Type, Any, List, Dict, Optional, Union, Literal, Tuple
from pydantic import BaseModel, Field

from parser.PDFParser import (
    PDFParser, 
    PyPDF2Parser,
    minerUParser
)
from parser.MarkdownParser import (
    MarkdownParser,
    NaiveMarkdownParser
)
from services.config import allowed_ips
from chunking.baseChunker import BaseChunker, Document
from chunking.textChunker import PunctuationChunker, RecursiveChunker
from chunking.codeChunker import PythonChunker
from chunking.htmlChunker import HTMLChunker
from chunking.markdownChunker import MarkdownChunker
from database.baseManager import BaseManager
from database.es.esManager import ESManager
from database.milvus.milvusManager import MilvusEmbeddingManager
from rerank.baseReranker import BaseReranker
from rerank.bgem3v2Reranker import BGEM3V2Reranker


##############################RequestTyping##############################
class PDFRequest(BaseModel):
    parse_strategy: str


class ChunkRequest(BaseModel):
    text: str
    chunk_strategy: str
    title: str = ""
    
    # 通用参数
    min_chunk_size: Optional[int] = 100
    max_chunk_size: Optional[int] = 200
    overlap_chunk_size: Optional[int] = 50
    
    # RecursiveChunker参数
    chunk_size: Optional[int] = 200
    separators: Optional[List[str]] = None
    keep_separator: Optional[Union[bool, Literal["start", "end"]]] = True
    is_separator_regex: Optional[bool] = False
    
    # PythonChunker参数
    # 继承自RecursiveChunker，已有参数覆盖
    
    # HTMLChunker参数
    html_headers_to_split_on: Optional[List[Tuple[str, str]]] = [
        ("h1", "Chapter"),
        ("h2", "Section"),
        ("h3", "Subsection")
    ]
    return_each_element: Optional[bool] = False
    
    # MarkdownChunker
    markdown_headers_to_split_on: Optional[List[Tuple[str, str]]] = [
        ("#", "h1"), 
        ("##", "h2"), 
        ("###", "h3"),
        ("####", "h4"),
        ("#####", "h5"),
        ("######", "h6")
    ]
    strip_headers: Optional[bool] = True
    return_each_line: Optional[bool] = False
    markdown_chunk_limit: Optional[int] = 200
    
    # 是否格式化块
    format_chunk_flag: bool = False


class IngestRequest(BaseModel):
    chunks_with_metadata: List[Dict]
    batch_size_limit: int
    collection_name: str
    database_strategy: str
    embedding_api: str = "openai_embedding_api"
    expand_fields: Optional[List[Dict]] = []
    expand_fields_values: Optional[Dict] = {}


class SearchRequest(BaseModel):
    query: str
    top_k: int
    collection_name: str
    database_strategy: str
    filter: Optional[str] = None


class RerankerRequest(BaseModel):
    query: str
    top_k: int
    rerank_strategy: str
    chunks_with_metadata: Optional[List[Dict]] = None


##############################StrategyMapping##############################
PDFPARSE_STRATEGY_MAP = {
    "pypdf2": PyPDF2Parser,
    "minerU": minerUParser
}

MARKDOWN_PARSER_STRATEGY_MAP = {
    "naive": NaiveMarkdownParser
}

CHUNK_STRATEGY_MAP = {
    "punctuation": PunctuationChunker,
    "recursive": RecursiveChunker,
    "python": PythonChunker,
    "html": HTMLChunker,
    "markdown": MarkdownChunker
}

DATABASE_STRATEGY_MAP = {
    "milvus": MilvusEmbeddingManager,
    # TODO
    "es": ...
}

RERANK_STRATEGY_MAP = {
    "bge-reranker-v2-m3": BGEM3V2Reranker
}


def authority_check(client_ip: str):
    # only allow registered ip to access
    if client_ip not in allowed_ips:
        logger.warning(f"Unknown ip is forbidden:{client_ip}")
        return False
    return True


def parse_pdf_file(file_content: bytes, parse_strategy: str) -> Dict:
    """
    Extract text from an PDF file using a specific parse strategy.
    """
    if parse_strategy not in PDFPARSE_STRATEGY_MAP:
        raise ValueError(f"Invalid parse strategy: '{parse_strategy}'. "
                    f"Valid strategies are: {', '.join(PDFPARSE_STRATEGY_MAP.keys())}")
    
    pdf_parser_obj: Type[PDFParser] = PDFPARSE_STRATEGY_MAP[parse_strategy]

    pdf_path = f"./__upload_file__/{uuid.uuid4().hex}.pdf"
    with open(pdf_path, "wb") as f:
        f.write(file_content)

    pdf_parser_instance = pdf_parser_obj(pdf_path=pdf_path)
    start_time = time.time()
    pdf_parser_instance.read_content()
    extracted_text = pdf_parser_instance.extract_text()
    end_time = time.time()

    os.remove(pdf_path)
    return {
        "status": "success",
        "extracted_text": extracted_text,
        "time_taken": end_time - start_time
    }


def parse_markdown_file(file_content: bytes, parse_strategy: str) -> Dict:
    """
    Extract text from an markdown file using a specific parse strategy.
    """
    if parse_strategy not in MARKDOWN_PARSER_STRATEGY_MAP:
        raise ValueError(f"Invalid parse strategy: '{parse_strategy}'. "
                  f"Valid strategies are: {', '.join(MARKDOWN_PARSER_STRATEGY_MAP.keys())}")
    
    markdown_parser_obj: Type[MarkdownParser] = MARKDOWN_PARSER_STRATEGY_MAP[parse_strategy]

    markdown_path = f"./__upload_file__/{uuid.uuid4().hex}.md"
    with open(markdown_path, "wb") as f:
        f.write(file_content)

    markdown_parser_instance = markdown_parser_obj(markdown_path=markdown_path) 
    start_time = time.time()
    markdown_parser_instance.read_content()
    extracted_text = markdown_parser_instance.extract_text()
    end_time = time.time()

    os.remove(markdown_path)
    return {
        "status": "success",
        "extracted_text": extracted_text,
        "time_taken": end_time - start_time
    }


def parse_doc_file(file_content: bytes, filename: str, parse_strategy: str) -> Dict:
    """
    Extract text from an uploaded document file using a specific parse strategy.
    """
    file_type = filename.split(".")[-1]

    if file_type == "pdf":
        return parse_pdf_file(file_content, parse_strategy)
    elif file_type == "md":
        return parse_markdown_file(file_content, parse_strategy)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
    

def process_chunk_text(request: ChunkRequest) -> List[Dict]:
    """
    Chunk text into smaller pieces.
    """
    if request.chunk_strategy not in CHUNK_STRATEGY_MAP:
        raise ValueError(f"Invalid chunk strategy: '{request.chunk_strategy}'. "
                  f"Valid strategies are: {', '.join(CHUNK_STRATEGY_MAP.keys())}")

    text = request.text
    title = request.title
    chunk_strategy = request.chunk_strategy

    # 准备参数
    chunker_kwargs = {}
    
    # 根据策略准备不同的参数
    if chunk_strategy == "punctuation":
        # 检查必要参数
        if request.min_chunk_size is None or request.max_chunk_size is None or request.overlap_chunk_size is None:
            raise ValueError("PunctuationChunker requires min_chunk_size, max_chunk_size, and overlap_chunk_size")
            
        chunker_kwargs = {
            "min_chunk_size": request.min_chunk_size,
            "max_chunk_size": request.max_chunk_size,
            "overlap_chunk_size": request.overlap_chunk_size
        }
        chunker_instance = PunctuationChunker()
    
    elif chunk_strategy == "recursive":
        # 检查必要参数
        if request.chunk_size is None:
            raise ValueError("RecursiveChunker requires chunk_size")
            
        init_kwargs = {}
        if request.chunk_size is not None:
            init_kwargs["chunk_size"] = request.chunk_size
        if request.separators is not None:
            init_kwargs["separators"] = request.separators
        if request.keep_separator is not None:
            init_kwargs["keep_separator"] = request.keep_separator
        if request.is_separator_regex is not None:
            init_kwargs["is_separator_regex"] = request.is_separator_regex
            
        chunker_instance = RecursiveChunker(**init_kwargs)
    
    elif chunk_strategy == "python":
        # 检查必要参数
        if request.chunk_size is None:
            raise ValueError("PythonChunker requires chunk_size")
            
        init_kwargs = {}
        if request.chunk_size is not None:
            init_kwargs["chunk_size"] = request.chunk_size
        if request.keep_separator is not None:
            init_kwargs["keep_separator"] = request.keep_separator
        if request.is_separator_regex is not None:
            init_kwargs["is_separator_regex"] = request.is_separator_regex
            
        chunker_instance = PythonChunker(**init_kwargs)
    
    elif chunk_strategy == "html":
        # 检查必要参数
        if request.html_headers_to_split_on is None:
            raise ValueError("HTMLChunker requires html_headers_to_split_on")
            
        init_kwargs = {}
        if request.html_headers_to_split_on is not None:
            init_kwargs["html_headers_to_split_on"] = request.html_headers_to_split_on
        if request.return_each_element is not None:
            init_kwargs["return_each_element"] = request.return_each_element
            
        chunker_instance = HTMLChunker(**init_kwargs)
    
    elif chunk_strategy == "markdown":
        # 检查必要参数
        if request.markdown_headers_to_split_on is None:
            raise ValueError("MarkdownChunker requires markdown_headers_to_split_on")
            
        init_kwargs = {}
        if request.markdown_headers_to_split_on is not None:
            init_kwargs["markdown_headers_to_split_on"] = request.markdown_headers_to_split_on
        if request.return_each_line is not None:
            init_kwargs["return_each_line"] = request.return_each_line
        if request.strip_headers is not None:
            init_kwargs["strip_headers"] = request.strip_headers
            
        chunker_instance = MarkdownChunker(**init_kwargs)
    
    else:
        # 未知的分块策略(虽然前面已经检查过了)
        raise ValueError(f"Unknown chunk strategy: {chunk_strategy}")

    # 执行分块
    start_time = time.time()
    chunked_docs = chunker_instance.chunk(text=text, title=title, **chunker_kwargs)
    end_time = time.time()
    
    if request.format_chunk_flag:
        chunked_text = [{"chunk": doc.format_chunk(), "metadata": doc.metadata} for doc in chunked_docs]
    else:
        chunked_text = [{"chunk": doc.chunk, "metadata": doc.metadata} for doc in chunked_docs]

    return {
        "status": "success",
        "message": f"Successfully chunk text to {len(chunked_text)} text chunks",
        "data": chunked_text,
        "time_taken": end_time - start_time
    }


def process_ingest_text(request: IngestRequest) -> Dict:
    """
    Ingest chunked text into the database.
    """
    if request.database_strategy not in DATABASE_STRATEGY_MAP:
        raise ValueError(f"Invalid database strategy: '{request.database_strategy}'. "
                  f"Valid strategies are: {', '.join(DATABASE_STRATEGY_MAP.keys())}")

    chunks_with_metadata = request.chunks_with_metadata
    batch_size_limit = request.batch_size_limit
    collection_name = request.collection_name
    database_strategy = request.database_strategy
    embedding_api = request.embedding_api
    expand_fields = request.expand_fields
    expand_fields_values = request.expand_fields_values
    
    # create and initialize the ingest instance 
    ingest_obj: Type[BaseManager] = DATABASE_STRATEGY_MAP[database_strategy]
    if issubclass(ingest_obj, MilvusEmbeddingManager):
        ingest_instance = ingest_obj(collection_name=collection_name, embedding_api=embedding_api, expand_fields=expand_fields)
    elif issubclass(ingest_obj, ESManager):
        # TODO
        # need to implement the initialization of es manager
        ingest_instance = None
        raise NotImplementedError("ES Manager not implemented yet")
    else:
        logger.error(f"ingest_obj is not one of the database manager subclass")
        raise ValueError("Invalid database manager class")

    # 将List[Dict]转换为List[Document]
    documents = []
    for item in chunks_with_metadata:
        chunk = item.get("chunk", "")
        metadata = item.get("metadata", {})
        documents.append(Document(chunk=chunk, metadata=metadata))

    # ingest the data
    start_time = time.time()
    ingest_return = ingest_instance.ingest(
        texts_with_metadata=documents, 
        batch_size_limit=batch_size_limit,
        **expand_fields_values
    )
    end_time = time.time()

    return {
        "status": "success",
        "message": f"Successfully ingested {len(chunks_with_metadata)} text chunks into database.",
        "ingest_return": json.dumps(ingest_return),
        "time_taken": end_time - start_time
    }


def process_search_text(request: SearchRequest) -> Dict:
    """
    Search for similar text in the database.
    """
    if request.database_strategy not in DATABASE_STRATEGY_MAP:
        raise ValueError(f"Invalid database strategy: '{request.database_strategy}'. "
                  f"Valid strategies are: {', '.join(DATABASE_STRATEGY_MAP.keys())}")
    
    query = request.query
    top_k = request.top_k
    collection_name = request.collection_name
    database_strategy = request.database_strategy
    filter = request.filter

     # create and initialize the search instance 
    search_obj: Type[BaseManager] = DATABASE_STRATEGY_MAP[database_strategy]
    if issubclass(search_obj, MilvusEmbeddingManager):
        search_instance = search_obj(collection_name=collection_name)
    elif issubclass(search_obj, ESManager):
        # TODO
        # need to implement the initialization of es manager
        search_instance = None
        raise NotImplementedError("ES Manager not implemented yet")
    else:
        logger.error(f"search_obj is not one of the database manager subclass")
        raise ValueError("Invalid database manager class")
    
    search_params = {"query": query,"top_k": top_k}
    if filter is not None:
        search_params.update({"filter": filter})

    # search the data
    start_time = time.time()
    results = search_instance.search(**search_params)
    end_time = time.time()

    return {
        "status": "success",
        "query": query,
        "results": results,
        "time_taken": end_time - start_time
    }


def process_rerank_results(request: RerankerRequest) -> Dict:
    """
    Re-rank search results using a specified strategy.
    """
    query = request.query
    top_k = request.top_k
    rerank_strategy = request.rerank_strategy
    chunks_with_metadata = request.chunks_with_metadata

    if rerank_strategy not in RERANK_STRATEGY_MAP:
        raise ValueError(f"Invalid rerank strategy: '{rerank_strategy}'. "
                  f"Valid strategies are: {', '.join(RERANK_STRATEGY_MAP.keys())}")

    sentences = [chunk_data.get("chunk", "") for chunk_data in chunks_with_metadata]
    
    if not sentences:
        raise ValueError("chunks_with_metadata must be provided and non-empty")

    # Create and initialize the reranker instance
    reranker_obj: Type[BaseReranker] = RERANK_STRATEGY_MAP[rerank_strategy]
    if issubclass(reranker_obj, BGEM3V2Reranker):
        reranker_instance = BGEM3V2Reranker()
    else:
        logger.error(f"reranker_obj is not one of the reranker subclass")
        raise ValueError("Invalid reranker class")

    # Perform re-ranking
    start_time = time.time()
    reranked_results = reranker_instance.rerank(query=query, top_k=top_k, sentences=sentences)
    end_time = time.time()

    # Format the results
    if reranked_results:
        formatted_results = []
        for i, result in enumerate(reranked_results):
            formatted_result = {
                "rank": i + 1, 
                "chunk": result.get("sentence"), 
                "score": result.get("score", 0.0)
            }
            
            # 如果提供了chunks_with_metadata，添加对应的metadata
            if chunks_with_metadata:
                # 在chunks_with_metadata中查找匹配的chunk
                for chunk_data in chunks_with_metadata:
                    if chunk_data.get("chunk") == result.get("sentence"):
                        # 将metadata添加到结果中
                        formatted_result["metadata"] = chunk_data.get("metadata", {})
                        break
                        
            formatted_results.append(formatted_result)
    else:
        formatted_results = []

    return {
        "status": "success",
        "query": query,
        "reranked_results": formatted_results,
        "time_taken": end_time - start_time
    }