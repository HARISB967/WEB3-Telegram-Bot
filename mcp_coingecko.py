# mcp_coingecko.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests, os
from dotenv import load_dotenv

load_dotenv()
CG_API_KEY = os.getenv("CG_API_KEY")
if not CG_API_KEY:
    raise RuntimeError("CG_API_KEY not set in environment")

app = FastAPI()
PRO_BASE = "https://pro-api.coingecko.com/api/v3"

@app.api_route("/{full_path:path}", methods=["GET"])
async def proxy_coingecko(request: Request, full_path: str):
    """
    Catch-all GET proxy: forwards /{full_path}?… → PRO_BASE/{full_path}?…
    and injects your Pro key as the x-cg-pro-api-key header.
    """
    url     = f"{PRO_BASE}/{full_path}"
    params  = dict(request.query_params)               # preserve all query params
    headers = {"x-cg-pro-api-key": CG_API_KEY}         # required Pro header

    upstream = requests.get(url, params=params, headers=headers, timeout=5)
    data     = upstream.json()

    return JSONResponse(status_code=upstream.status_code, content=data)
