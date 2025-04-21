import time
import sys

sys.path.append(".")
sys.path.append("..")

from database.milvus.milvusManager import MilvusEmbeddingManager
from chunking.textChunker import PunctuationChunker
from parser.PDFParser import PyPDF2Parser
from rerank.bgem3v2Reranker import BGEM3V2Reranker  # Import the BGEM3V2Reranker

def test_embedding_and_retrieval():
    pdf_path = "test.pdf"
    collection_name = "test_local_collection"
    pdfParser = PyPDF2Parser(pdf_path=pdf_path)
    pdfParser.read_content()
    extracted_text = pdfParser.extract_text()
    print(extracted_text)

    print("=== Text Chunking ===")
    chunker = PunctuationChunker(text=extracted_text)
    chunked_text = chunker.chunk(
        min_chunk_size=100, 
        max_chunk_size=200, 
        overlap_chunk_size=0
    )

    for i, each_chunked_text in enumerate(chunked_text):
        print(f"Chunk {i} : {each_chunked_text}")
        print()
    
    # # Data ingestion test
    # print("=== Data Ingestion Test ===")
    # start_time = time.time()
    # processor = MilvusEmbeddingManager(collection_name=collection_name) 
    # processor.ingest(chunked_text[:3], batch_size_limit=16)
    # end_time = time.time()
    # print(f"Successfully inserted {len(chunked_text[:3])} text chunks into Milvus. Time elapsed: {end_time - start_time}")
    
    # # Search test
    # print("\n=== Search Test ===")
    # start_time = time.time()
    # query = "2020年CPI上涨了多少"
    # results = processor.search(query=query, top_k=10)  # Retrieve top-10 results initially for reranking
    # end_time = time.time()
    # print("Raw results: ", results)
    # print(f"Search time elapsed: {end_time - start_time}")
    
    # # Reranking process
    # print("\n=== Reranking Test ===")
    # reranker = BGEM3V2Reranker()  # Instantiate the reranker
    # reranked_results = reranker.rerank(query=query, top_k=3, sentences=results)  # Re-rank top-10 results to top-3

    # # Print reranking results
    # print("\nQuery: ", query)
    # print("Top-3 Similar Texts after Reranking:")
    # if reranked_results:
    #     for i, result in enumerate(reranked_results, 1):
    #         print(f"{i}. Sentence: {result.get('sentence')}, Score: {result.get('score', 0.0):.4f}")
    # else:
    #     print("Reranking failed.")

if __name__ == "__main__":
    # Run the test
    test_embedding_and_retrieval()
