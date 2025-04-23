import json
import requests


BASE_URL = "http://127.0.0.1:17724"


def test_pdf_2_text(parse_strategy="pypdf2"):
    """
    Test the /pdf_2_text endpoint.
    """
    print("=== Testing /pdf_2_text ===")
    pdf_path = "dummy_file/DeepSeek_R1.pdf" 
    
    try:
        with open(pdf_path, "rb") as pdf_file:
            files = {"file": (pdf_file.name, pdf_file, "application/pdf")}
            # Since upload file, http will use default multipart/form-data
            # which require 'data' Form instead of whole json
            # this 'data' will be parsed by depended parser declared in server
            data = {"data": json.dumps({"parse_strategy": parse_strategy})}
            
            response = requests.post(
                f"{BASE_URL}/pdf_2_text",
                files=files,
                data=data
            )
    
        if response.status_code == 200:
            print("Success! Extracted text:")
            result = response.json()
            extracted_text = result.get("extracted_text", "")
            print(extracted_text[:500])  # 打印前 500 个字符
            print(f"Time taken: {result.get('time_taken')} seconds")
            return extracted_text
        else:
            print(f"Error: {response.status_code}, {response.json().get('detail')}")
            return None
    except Exception as e:
        print(f"Client-side error: {str(e)}")
        return None

def test_chunk_text(
    extracted_text, 
    chunk_strategy="punctuation"
):
    """
    Test the /chunk_text endpoint.
    """
    print("\n=== Testing /chunk_text ===")
    payload = {
        "text": extracted_text,
        # "min_chunk_size": 100,
        # "max_chunk_size": 200,
        # "overlap_chunk_size": 10,
        "chunk_size": 200,
        "keep_separator": False,
        "chunk_strategy": chunk_strategy,
        "title": "test.pdf",
        "format_chunk_flag": True
    }
    response = requests.post(f"{BASE_URL}/chunk_text", json=payload)
    
    if response.status_code == 200:
        print("Success! Chunked text:")
        chunks = response.json().get("data", [])
        print(f"First 3 chunks: {chunks[:3]}")
        return chunks
    else:
        print(f"Error: {response.status_code}, {response.json().get('detail')}")
        return None


def test_ingest_text(
    chunks, 
    collection_name="test_service_collection", 
    database_strategy="milvus",
    expand_fields = [],
    expand_fields_values = {}
):
    """
    Test the /ingest_text endpoint.
    """
    print("\n=== Testing /ingest_text ===")
    payload = {
        "chunks_with_metadata": chunks,
        "batch_size_limit": 16,
        "collection_name": collection_name,
        "database_strategy": database_strategy,
        "expand_fields": expand_fields,
        "expand_fields_values": expand_fields_values
    }
    response = requests.post(
        f"{BASE_URL}/ingest_text", json=payload, timeout=1000)
    
    if response.status_code == 200:
        print("Success! Text ingested.")
        print(response.json())
    else:
        print(f"Error: {response.status_code}, {response.json()}")


def test_reranker(
    query, 
    sentences, 
    top_k=3,
    rerank_strategy="bge-reranker-v2-m3"
):
    """
    Test the /rerank endpoint.
    """
    print("\n=== Testing /rerank ===")
    payload = {
        "query": query,
        "top_k": top_k,
        "chunks_with_metadata": sentences,
        "rerank_strategy": rerank_strategy 
    }
    response = requests.post(f"{BASE_URL}/rerank", json=payload)

    if response.status_code == 200:
        print("Success! Reranked results:")
        results = response.json()
        reranked_results = results.get("reranked_results", [])
        print(f"{reranked_results = }")
    else:
        print(f"Error: {response.status_code}, {response.json().get('detail')}")


def test_milvus_search_and_rerank(
    query, 
    collection_name="test_service_collection", 
    milvus_top_k=20, 
    rerank_top_k=3,
    database_strategy="milvus",
    rerank_strategy="bge-reranker-v2-m3",
    filter = None
):
    """
    Test the /milvus_search endpoint.
    """
    print("\n=== Testing /milvus_search ===")
    payload = {
        "query": query,
        "top_k": milvus_top_k,
        "collection_name": collection_name,
        "batch_size_limit": 16,
        "database_strategy": database_strategy,
        "filter": filter
    }
    response = requests.post(f"{BASE_URL}/milvus_search", json=payload)
    
    if response.status_code == 200:
        print("Success! Query result:")
        results = response.json()
        print(f"Search results: {results}")
    else:
        print(f"Error: {response.status_code}, {response.json().get('detail')}")

    if response.status_code == 200:
        search_results = response.json().get("results", [])

        # Step 5: Test Reranker
        test_reranker(
            query=query, 
            sentences=search_results, 
            top_k=rerank_top_k,
            rerank_strategy=rerank_strategy
        )
    else:
        print(f"\n--- Search Test Failed. Aborting Reranker Test... ---")
        print(f"Error: {response.status_code}, {response.json().get('detail')}")
    print("\n--- Testing Sequence Complete ---")
    

def run_all_tests():
    """
    Run all tests sequentially.
    """
    collection_name = "test_20250415_collection"

    # Step 1: Test PDF to text extraction
    print("\n--- Starting Test Sequence ---")
    extracted_text = test_pdf_2_text(parse_strategy="minerU")
    if not extracted_text:
        print("\n--- Extraction Test Failed. Aborting... ---")
        return

    # Step 2: Test text chunking
    chunks = test_chunk_text(
        extracted_text, 
        chunk_strategy="recursive"
    )
    if not chunks:
        print("\n--- Chunking Test Failed. Aborting... ---")
        return

    print("after chunking chunks: ", chunks)

    # Step 3: Test text ingestion
    test_ingest_text(
        chunks, 
        collection_name=collection_name, 
        database_strategy="milvus",
        expand_fields = [{"name": "summary_doc_id", "dtype": "INT64"}],
        expand_fields_values={"summary_doc_id": 789456}
    )

    # Step 4: Test Milvus search and reranker
    test_milvus_search_and_rerank(
        query="2020年CPI上涨了多少", 
        collection_name=collection_name, 
        milvus_top_k=20,
        rerank_top_k=10, 
        database_strategy="milvus",
        rerank_strategy="bge-reranker-v2-m3",
        filter="summary_doc_id == 789456"
    )
    print("\n--- Testing Sequence Complete ---")


if __name__ == "__main__":
    run_all_tests()
