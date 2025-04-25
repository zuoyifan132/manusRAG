from tqdm import tqdm
from loguru import logger
from typing import List, Optional, Dict, Any
from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema
import sys

sys.path.append("../..")

from database.milvus.config import VECTOR_DIM, MILVUS_URI, LOCAL_MILVUS_LITE_DB_PATH
from utils.embedding_api import bge_m3_embedding_api, openai_embedding_api, milvus_model_embedding
from database.baseManager import BaseManager
from chunking.baseChunker import Document


DATA_TYPE_MAPPING = {
    "INT64": DataType.INT64,
    "FLOAT_VECTOR": DataType.FLOAT_VECTOR,
    "VARCHAR": DataType.VARCHAR,
    "JSON": DataType.JSON,
    "BOOL": DataType.BOOL,
    "FLOAT": DataType.FLOAT,
    "DOUBLE": DataType.DOUBLE
}


class MilvusEmbeddingManager(BaseManager):
    """
    Milvus Embedding Manager, inheriting from BaseManager.
    Manages embeddings in the Milvus database, including ingesting and searching functionality.
    """
    def __init__(
        self, 
        collection_name="text_collection", 
        embedding_api="openai_embedding_api", 
        expand_fields=None, 
        use_milvus_lite=True, 
        db_path=LOCAL_MILVUS_LITE_DB_PATH
    ):
        super().__init__(collection_name=collection_name)
        if embedding_api == "bge_m3_embedding_api":
            self.embedding = bge_m3_embedding_api
        elif embedding_api == "openai_embedding_api":
            self.embedding = openai_embedding_api
        elif embedding_api == "milvus_model_embedding":
            self.embedding = milvus_model_embedding
        else:
            raise ValueError(f"Unsupported embedding API: {embedding_api}")

        # try:
        # Connect to the Milvus database
        if use_milvus_lite:
            # 使用Milvus Lite本地文件连接
            self.client = MilvusClient(uri=db_path)
            logger.info(f"Using Milvus Lite with local database file: {db_path}")
        else:
            # 使用远程Milvus服务器连接
            self.client = MilvusClient(uri=MILVUS_URI, token="root:Milvus")
            logger.info(f"Using remote Milvus server at: {MILVUS_URI}")

        # Create the collection if it doesn't exist
        if not self.client.has_collection(collection_name=self.collection_name):
            self._create_collection(self.collection_name, expand_fields)
        
        # Ensure the collection is loaded
        self.client.load_collection(self.collection_name)
        logger.info(f"Successfully connected to collection: {self.collection_name}")
        
        # except Exception as e:
        #     logger.error(f"Failed to initialize the Milvus client: {str(e)}")
        #     raise

    def _create_collection(self, collection_name, expand_fields):
        """
        Create a Milvus collection and build an index for the vector field.
        
        Args:
            collection_name (str): The name of the collection.
        """
        # Define default fields
        defaulted_fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        
        fields = defaulted_fields.copy()  # Initialize fields with the default set
        
        # Process expand_fields if not empty
        if expand_fields:
            logger.info(f"Using expand_fields: {expand_fields} to create Milvus collection")
            for field_def in expand_fields:
                field_name = field_def.get("name")
                field_dtype = field_def.get("dtype")

                if not field_name or not field_dtype:
                    logger.error(f"Invalid expand field definition: {field_def}. Both 'name' and 'dtype' are required.")
                    raise ValueError(f"Invalid expand field definition: {field_def}")

                if field_dtype not in DATA_TYPE_MAPPING:
                    logger.error(f"Unsupported field dtype: {field_dtype}. Allowed dtypes are {list(DATA_TYPE_MAPPING.keys())}")
                    raise ValueError(f"Unsupported field dtype: {field_dtype}")

                milvus_dtype = DATA_TYPE_MAPPING[field_dtype]
                
                # Create new field schema
                new_field = FieldSchema(name=field_name, dtype=milvus_dtype)
                fields.append(new_field)
                logger.info(f"Added field '{field_name}' with dtype '{field_dtype}' to collection schema.")
        
        # Create the collection schema
        schema = CollectionSchema(fields=fields, description="text collection with JSON metadata")
        
        # Create the collection
        self.client.create_collection(
            collection_name=collection_name,
            schema=schema
        )
        
        # Define index parameters
        index_params = MilvusClient.prepare_index_params()
        index_params.add_index(
            field_name="vector", 
            index_type="FLAT", 
            index_name="vector_index", 
            metric_type="IP",
            # params={
            #     "M": 64,  # Maximum number of connections per node
            #     "efConstruction": 100  # Number of candidate nodes to consider during index construction
            # }
        )
        
        # Create the index for the vector field
        self.client.create_index(
            collection_name=collection_name,
            index_params=index_params
        )
        logger.info(f"Successfully created an index for the 'vector' field in collection {collection_name}")

    def get_collection(self):
        return self.client.list_collections()

    def ingest(self, texts_with_metadata: List[Document], batch_size_limit: int = 16, **kwargs):
        """
        Process and store a batch of Document objects into Milvus.
        If the batch size exceeds the limit, process in chunks.
        
        Args:
            texts_with_metadata (List[Document]): List of Document objects to process and store.
            batch_size_limit (int): Maximum batch size for processing.
        """

        ingest_return_value_set = []
        if len(texts_with_metadata) > batch_size_limit:
            # Process in chunks
            for i in tqdm(range(0, len(texts_with_metadata), batch_size_limit), desc="Ingesting batch data into Milvus: "):
                batch = texts_with_metadata[i:i + batch_size_limit]
                ingest_return_value_set.append(self._ingest_batch(batch, **kwargs))
        else:
            ingest_return_value_set.append(self._ingest_batch(texts_with_metadata, **kwargs))

        return ingest_return_value_set

    def _ingest_batch(self, texts_with_metadata: List[Document], **kwargs):
        """
        Helper method to process and store a single batch of Document objects.
        Generate embedding vectors and insert them into Milvus.
        
        Args:
            texts_with_metadata (List[Document]): A batch of Document objects.
        """
        try:
            # 提取所有文档的chunk用于生成嵌入向量
            chunks = [doc.chunk for doc in texts_with_metadata]
            
            # 生成嵌入向量
            embeddings = self.embedding(texts=chunks)

            # 准备插入数据
            data = []
            for embedding, doc in zip(embeddings, texts_with_metadata):
                items_to_ingest = {
                    "vector": embedding, 
                    "text": doc.chunk,
                    "metadata": doc.metadata
                }
                if kwargs:
                    items_to_ingest.update(kwargs)
                data.append(items_to_ingest)
            
            # 插入到Milvus
            ingest_return_value = self.client.insert(
                collection_name=self.collection_name,
                data=data
            )
            logger.info(f"Successfully inserted {len(texts_with_metadata)} records into collection {self.collection_name}")

            ingest_return_value.update({"ids": list(ingest_return_value["ids"])})

            return ingest_return_value
        except Exception as e:
            logger.error(f"Error occurred during the insertion process: {str(e)}")

    def search(self, query: str, top_k: int = 3, **kwargs) -> Optional[List[Dict[str, Any]]]:
        """
        Perform a top-k similarity search.
        Returns the top-k most similar documents in the database for the query.
        
        Args:
            query (str): The search query text.
            top_k (int): The number of top results to retrieve.
            expr (str): Optional filtering expression.
        
        Returns:
            A list of dictionaries containing text and metadata, or None if the search fails.
        """
        if not query or not query.strip():
            logger.error("Query text cannot be empty")
            return None
            
        try:
            # Generate an embedding vector for the query
            query_embedding = self.embedding([query])
            if not query_embedding:
                logger.error("Failed to generate embedding vector for the query")
                return None
                
            # Search in Milvus
            search_params = {"metric_type": "IP", "params": {"ef": 10}}
            
            # Build search arguments
            search_args = {
                "collection_name": self.collection_name,
                "data": [query_embedding[0]],
                "limit": top_k,
                "output_fields": ["text", "metadata", "id"],
                "search_params": search_params,
            }
                
            # Add any additional kwargs
            search_args.update(kwargs)
            
            results = self.client.search(**search_args)
            
            # Extract and return the documents with text and metadata
            documents = []
            for hit in results[0]:
                documents.append({
                    "chunk": hit["entity"]["text"],
                    "metadata": hit["entity"]["metadata"],
                    "score": hit["distance"],
                    "id": hit["entity"]["id"]
                })
            return documents
            
        except Exception as e:
            logger.error(f"Error occurred during the search process: {str(e)}")
            return None
        

if __name__ == "__main__":
    collection_name = "my_custom_collection"
    # 定义自定义字段
    expand_fields = [
        {"name": "summary_doc_id", "dtype": "INT64"},  # 整数类型的summary_doc_id字段
    ]
    
    # 创建 MilvusEmbeddingManager 示例 - 使用Milvus Lite
    manager = MilvusEmbeddingManager(
        collection_name=collection_name, 
        expand_fields=expand_fields,
        use_milvus_lite=True,  # 启用Milvus Lite
        db_path="./my_vector_db.db"  # 指定本地数据库文件路径
    )
    
    logger.info("MilvusEmbeddingManager 创建成功，使用Milvus Lite本地数据库!")
    
    # 创建示例文档
    sample_documents = [
        Document(
            chunk="这是第一个文档的内容，包含了一些重要信息。jfgj",
            metadata={"source": "sample_source_1", "author": "张三", "date": "2023-05-01"}
        ),
        Document(
            chunk="这是第二个文档的内容，描述了一个有趣的案例。gjhgkg",
            metadata={"source": "sample_source_2", "author": "李四", "date": "2023-05-02"}
        ),
        Document(
            chunk="这是第三个文档，讨论了一些技术细节和实现方法。gkghkbkj",
            metadata={"source": "sample_source_3", "author": "王五", "date": "2023-05-03"}
        )
    ]
    
    # 插入文档时包含额外的summary_doc_id字段
    try:
        # 调用ingest方法，传入额外的summary_doc_id参数
        result = manager.ingest(sample_documents, summary_doc_id=789456)
        logger.info(f"成功插入数据，返回值: {result}")
        
        # 测试搜索功能
        search_results = manager.search("技术细节", top_k=3)
        if search_results:
            logger.info(f"搜索结果: {search_results}")
        else:
            logger.warning("没有找到匹配的搜索结果")

        collections = manager.get_collection()
        logger.info(f"collections: {collections}")
            
    except Exception as e:
        logger.error(f"插入或搜索过程中发生错误: {str(e)}")

    # 如果要使用远程Milvus服务器，可以这样创建:
    # remote_manager = MilvusEmbeddingManager(
    #     collection_name="remote_collection", 
    #     expand_fields=expand_fields,
    #     use_milvus_lite=False  # 使用远程Milvus服务器
    # )