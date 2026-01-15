# mcp_glassnode.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests, os
from dotenv import load_dotenv

load_dotenv()
GLASSNODE_API_KEY = os.getenv("GLASSNODE_API_KEY")
if not GLASSNODE_API_KEY:
    raise RuntimeError("GLASSNODE_API_KEY not set")

app = FastAPI()
GLASSNODE_BASE = "https://api.glassnode.com/v1/metrics"

@app.get("/glassnode/{group}/{metric}")
async def glassnode_proxy(group: str, metric: str, request: Request):
    # Collect all query params, including asset → a
    params = dict(request.query_params)
    params["api_key"] = GLASSNODE_API_KEY

    url = f"{GLASSNODE_BASE}/{group}/{metric}"
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return JSONResponse(content=resp.json())
    except requests.HTTPError as e:
        # pass through status codes
        return JSONResponse(status_code=resp.status_code, content={"error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
