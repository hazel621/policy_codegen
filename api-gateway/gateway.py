# gateway.py
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

CODEGEN_SERVICE_URL = "http://codegen-service:8000"  # Docker 内部服务名或 host

async def forward_request(method: str, path: str, request: Request):
    body = await request.body()
    headers = dict(request.headers)

    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method=method,
            url=f"{CODEGEN_SERVICE_URL}{path}",
            content=body,
            headers=headers
        )
    return resp.json()

@app.post("/api/roles")
async def gateway_roles(request: Request):
    return await forward_request("POST", "/roles", request)

@app.post("/api/actions")
async def gateway_actions(request: Request):
    return await forward_request("POST", "/actions", request)

@app.post("/api/duties")
async def gateway_duties(request: Request):
    return await forward_request("POST", "/duties", request)

@app.post("/api/powers")
async def gateway_powers(request: Request):
    return await forward_request("POST", "/powers", request)

@app.post("/api/violations")
async def gateway_violations(request: Request):
    return await forward_request("POST", "/violations", request)

@app.post("/api/action-handlers")
async def gateway_handlers(request: Request):
    return await forward_request("POST", "/action-handlers", request)
