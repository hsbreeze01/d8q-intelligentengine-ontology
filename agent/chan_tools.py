"""
Agent tool definitions for Compass Agent (Function Calling).
These are the 3 tools the LLM agent will use.
"""
from typing import List, Dict, Any
from store import get_store
from sparql.chan_queries import (
    get_structure, verify_buy_point, explain_signal, get_multi_level_summary
)


async def get_chan_structure(symbol: str) -> List[Dict[str, Any]]:
    """
    获取标的在所有级别的缠论结构（笔、线段、中枢）。
    返回统一列表，每项含 type, id, level, 高低价/中枢区间等。
    """
    store = get_store()
    return get_structure(store, symbol)


async def verify_buy_points(symbol: str) -> List[Dict[str, Any]]:
    """
    校验该标的当前所有买点有效性（是否被中枢/线段确认、级别、类型）。
    """
    store = get_store()
    return verify_buy_point(store, symbol)


async def explain_buy_point(signal_id: str) -> List[Dict[str, Any]]:
    """
    给定一个买卖点 IRI，返回其完整证据链（确认结构、价格、时间、类型）。
    用于 Agent 生成研报解释。
    """
    store = get_store()
    return explain_signal(store, signal_id)


async def get_level_summary(symbol: str) -> Dict[str, Any]:
    """
    获取标的多级别概览：各级别笔数、中枢数、最新买卖点。
    """
    store = get_store()
    return get_multi_level_summary(store, symbol)


# ---------- OpenAI Function Schemas ----------
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_chan_structure",
            "description": "获取标的的缠论多级别结构（笔/线段/中枢），用于判断当前走势位置",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "标的代码，如 000001.SZ"}
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verify_buy_points",
            "description": "校验标的当前所有买点的有效性与级别",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "标的代码，如 000001.SZ"}
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explain_buy_point",
            "description": "解释某个具体买卖点的证据链（被哪个中枢/线段确认、价格、时间、类型）",
            "parameters": {
                "type": "object",
                "properties": {
                    "signal_id": {"type": "string", "description": "买卖点完整IRI，如 http://d8q.com/chan/000001.SZ_D_buy_123"}
                },
                "required": ["signal_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_level_summary",
            "description": "获取标的多级别概览：各级别笔数、中枢数",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "标的代码，如 000001.SZ"}
                },
                "required": ["symbol"]
            }
        }
    }
]

# ---------- Tool Dispatcher ----------
async def dispatch_tool(name: str, args: dict) -> Any:
    mapping = {
        "get_chan_structure": get_chan_structure,
        "verify_buy_points": verify_buy_points,
        "explain_buy_point": explain_buy_point,
        "get_level_summary": get_level_summary,
    }
    if name not in mapping:
        raise ValueError(f"Unknown tool: {name}")
    return await mapping[name](**args)