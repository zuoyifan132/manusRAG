# -*- coding: utf-8 -*-
# Created on 2025/4/8
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import CrossEncoder
import uvicorn
from loguru import logger
import sys
import os


# Configure loguru logging
logger.remove()  # Remove default log handler
logger.add(sys.stdout, level="INFO")  # Output to console

# Initialize FastAPI application
app = FastAPI(title="BGE Reranker Service")
# Load BGE-Reranker-v2-m3 model
logger.info("Loading BGE-Reranker-v2-m3 model...")


try:
    model = CrossEncoder("BAAI/bge-reranker-v2-m3")
    logger.info("Model loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    raise


# Define request body data model
class RerankRequest(BaseModel):
    query: str
    top_k: int
    sentences: list[str]


# Define reranking endpoint
@app.post("/rerank")
async def rerank(request: RerankRequest):
    try:
        # Log request details
        logger.debug(f"Received request: query='{request.query}', sentences={request.sentences}")
        # Extract query and sentences
        query = request.query
        top_k = request.top_k
        sentences = request.sentences

        if not query or not sentences:
            logger.warning("Empty query or sentences received.")
            raise HTTPException(status_code=400, detail="Query and sentences must not be empty")

        # Construct query-sentence pairs
        pairs = [[query, sentence] for sentence in sentences]
        logger.debug(f"Constructed {len(pairs)} query-sentence pairs.")

        # Compute scores using the model
        logger.info("Computing scores...")
        scores = model.predict(pairs)
        logger.info("Scores computed successfully.")

        # Prepare results, sorted by score in descending order
        results = [
            {"sentence": sentence, "score": float(score)}
            for sentence, score in zip(sentences, scores)
        ]
        results = sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]
        # Log response details
        logger.debug(f"Returning top_k results: {results}")
        return {"results": results}
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.get("/health")
async def check_health() -> dict:
    """Check the health of the service"""
    return {"status": "ok"}


# Run the service
if __name__ == "__main__":
    port = int(os.getenv("RERANKER_PORT", 12212))
    logger.info(f"Starting FastAPI service on 0.0.0.0:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)