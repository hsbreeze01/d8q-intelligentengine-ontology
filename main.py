"""
d8q-intelligentengine-ontology: FastAPI entry point.
Exposes SPARQL endpoint + Agent tool APIs.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from store import get_store, reload_ontology
from sync.ingest import ingest
from agent.chan_tools import dispatch_tool, TOOL_SCHEMAS
import json

app = FastAPI(
    title="d8q-intelligentengine-ontology",
    description="缠论知识图谱服务：三元组存储 + SPARQL + Agent Tool",
    version="0.1.0",
)


# ---------- Lifecycle ----------
@app.on_event("startup")
async def startup():
    get_store()
    print("[startup] Oxigraph store ready")


# ---------- Health ----------
@app.get("/healthz")
async def healthz():
    store = get_store()
    return {"status": "ok", "triples": len(store)}


@app.get("/readyz")
async def readyz():
    store = get_store()
    return {"status": "ready", "triples": len(store)}


# ---------- SPARQL Endpoint ----------
@app.post("/sparql", response_class=PlainTextResponse)
async def sparql_endpoint(request: Request):
    """Standard SPARQL 1.1 endpoint (POST)."""
    body = await request.body()
    query = body.decode("utf-8") if body else ""
    if not query:
        raise HTTPException(status_code=400, detail="Empty query")
    try:
        store = get_store()
        results = store.query(query)
        # Convert to SPARQL JSON Results format
        variables = results.variables  # list of Variable objects
        rows = []
        for row in results:
            d = {}
            for var in variables:
                val = row[var]
                if val is not None:
                    d[var.value] = {"value": str(val), "type": "literal"}
            rows.append(d)
        return json.dumps({"results": {"bindings": rows}}, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- Ingest API ----------
class IngestRequest(BaseModel):
    symbol: str
    level: str
    strokes: Optional[List[Dict[str, Any]]] = None
    segments: Optional[List[Dict[str, Any]]] = None
    centers: Optional[List[Dict[str, Any]]] = None
    buy_points: Optional[List[Dict[str, Any]]] = None


class IngestResponse(BaseModel):
    symbol: str
    level: str
    ingested: int


@app.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(req: IngestRequest):
    """接收规则引擎输出的缠论结构数据，写入三元组存储。"""
    store = get_store()
    result = ingest(
        store,
        symbol=req.symbol,
        level=req.level,
        strokes=req.strokes,
        segments=req.segments,
        centers=req.centers,
        buy_points=req.buy_points,
    )
    return result


# ---------- Agent Tool APIs ----------
class ToolRequest(BaseModel):
    symbol: Optional[str] = None
    signal_id: Optional[str] = None


@app.post("/tools/get_chan_structure")
async def tool_get_structure(req: ToolRequest):
    if not req.symbol:
        raise HTTPException(status_code=400, detail="symbol is required")
    result = await dispatch_tool("get_chan_structure", {"symbol": req.symbol})
    return result


@app.post("/tools/verify_buy_points")
async def tool_verify(req: ToolRequest):
    if not req.symbol:
        raise HTTPException(status_code=400, detail="symbol is required")
    result = await dispatch_tool("verify_buy_points", {"symbol": req.symbol})
    return result


@app.post("/tools/explain_buy_point")
async def tool_explain(req: ToolRequest):
    if not req.signal_id:
        raise HTTPException(status_code=400, detail="signal_id is required")
    result = await dispatch_tool("explain_buy_point", {"signal_id": req.signal_id})
    return result


@app.post("/tools/get_level_summary")
async def tool_summary(req: ToolRequest):
    if not req.symbol:
        raise HTTPException(status_code=400, detail="symbol is required")
    result = await dispatch_tool("get_level_summary", {"symbol": req.symbol})
    return result


# ---------- Reload ----------
@app.post("/admin/reload")
async def reload():
    """Force reload ontology files."""
    store = reload_ontology()
    return {"status": "reloaded", "triples": len(store)}


# ---------- Tool Schemas (for LLM registration) ----------
@app.get("/tools/schemas")
async def tool_schemas():
    """Return OpenAI function schemas for all tools."""
    return TOOL_SCHEMAS


if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)