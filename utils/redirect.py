# -*- coding: utf-8 -*-
# Created on 2025/4/2
# This file is for embedding and reranker redirect services
from fastapi import FastAPI, Request
import httpx
import uvicorn


app = FastAPI()


@app.post("/bge_m3_embedding")
async def generate(req: dict, request: Request) -> dict:
    headers = {"content-type": "application/json"}

    print("req: ", req)

    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            url="http://10.200.64.10/10-bge-m3-embedding/embedding",
            json=req,
            headers=headers
        )
        print(response)
    return response.json()


@app.post("/rerank")
async def generate(req: dict, request: Request) -> dict:
    headers = {"content-type": "application/json"}

    print("req: ", req)

    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            url="http://10.200.64.10/10-bge-reranker-v2-m3/rerank",
            json=req,
            headers=headers
        )
        print(response)
    return response.json()


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=13456)