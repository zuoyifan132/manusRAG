import json
import sys
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends, Request
from fastapi.responses import JSONResponse
from typing import Optional, Union

sys.path.append(".")
sys.path.append("..")

from services.service import (
    PDFRequest, 
    ChunkRequest,
    IngestRequest,
    SearchRequest,
    RerankerRequest,
    authority_check,
    parse_pdf_file,
    parse_doc_file,
    process_chunk_text,
    process_ingest_text,
    process_search_text,
    process_rerank_results
)
from services.pipeline import (
    PipelineRequest, 
    run_pipeline
)

# FastAPI app
app = FastAPI()


def parse_pdf_request_json_data(data: str = Form(...)) -> PDFRequest:
    """
    Using Form to decalre that this request is from multipart/form-data
    """
    try:
        json_data = json.loads(data)
        return PDFRequest(**json_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid data: {str(e)}")
    

def parse_pipeline_request_json_data(data: str = Form(...)) -> PipelineRequest:
    """
    Using Form to decalre that this request is from multipart/form-data
    """
    try:
        json_data = json.loads(data)
        return PipelineRequest(**json_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid data: {str(e)}")


@app.post("/pdf_2_text")
async def extract_text(
    file: UploadFile = File(...),
    request: PDFRequest = Depends(parse_pdf_request_json_data),
    fastapi_request: Request = None
):
    """
    Extract text from an uploaded PDF file using a specific parse strategy.
    """
    client_ip = fastapi_request.client.host
    if not authority_check(client_ip):
        raise HTTPException(status_code=403, detail="Forbidden: IP not allowed.")

    try:
        file_content = await file.read()
        result = parse_pdf_file(file_content, request.parse_strategy)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")


@app.post("/doc_2_text")
async def extract_text_doc(
    file: UploadFile = File(...),
    request: PDFRequest = Depends(parse_pdf_request_json_data),
    fastapi_request: Request = None
):
    """
    Extract text from an uploaded document file using a specific parse strategy.
    """
    client_ip = fastapi_request.client.host
    if not authority_check(client_ip):
        raise HTTPException(status_code=403, detail="Forbidden: IP not allowed.")

    try:
        file_content = await file.read()
        result = parse_doc_file(file_content, file.filename, request.parse_strategy)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")


@app.post("/chunk_text")
async def chunk_text(request: ChunkRequest):
    """
    Chunk text into smaller pieces.
    """
    try:
        result = process_chunk_text(request)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to chunk text: {str(e)}")
    

@app.post("/ingest_text")
async def ingest_text(request: IngestRequest, fastapi_request: Request):
    """
    Ingest chunked text into the database.
    """
    client_ip = fastapi_request.client.host
    if not authority_check(client_ip):
        raise HTTPException(status_code=403, detail="Forbidden: IP not allowed.")

    try:
        result = process_ingest_text(request)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest text: {str(e)}")


@app.post("/milvus_search")
async def search_text(request: SearchRequest, fastapi_request: Request):
    """
    Search for similar text in the database.
    """
    client_ip = fastapi_request.client.host
    if not authority_check(client_ip):
        raise HTTPException(status_code=403, detail="Forbidden: IP not allowed.")
    
    try:
        result = process_search_text(request)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search for text: {str(e)}")


@app.post("/rerank")
async def rerank_results(request: RerankerRequest, fastapi_request: Request):
    """
    Re-rank search results using a specified strategy.
    """
    client_ip = fastapi_request.client.host
    if not authority_check(client_ip):
        raise HTTPException(status_code=403, detail="Forbidden: IP not allowed.")

    try:
        result = process_rerank_results(request)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to re-rank results: {str(e)}")


@app.post("/pipeline")
async def execute_pipeline(
    file: Optional[UploadFile] = File(None),
    request_data: PipelineRequest = Depends(parse_pipeline_request_json_data),
    fastapi_request: Request = None
):
    """
    执行完整的RAG流程。
    支持同时上传文件和配置数据。
    """
    client_ip = fastapi_request.client.host
    if not authority_check(client_ip):
        raise HTTPException(status_code=403, detail="Forbidden: IP not allowed.")
    
    file_content = None
    filename = None
    
    try:
        # 如果上传了文件，读取文件内容
        if file:
            file_content = await file.read()
            filename = file.filename
        
        # 运行pipeline, 传递所有参数给pipeline.py处理
        result = run_pipeline(
            config=request_data.config, 
            file_content=file_content,
            filename=filename,
            query=request_data.query
        )
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute pipeline: {str(e)}")


# Optional root endpoint
@app.get("/")
async def root():
    """
    Root endpoint to confirm the service is running.
    """
    return JSONResponse(content={"message": "PDF Processing and Retrieval service is running!"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=17724) 