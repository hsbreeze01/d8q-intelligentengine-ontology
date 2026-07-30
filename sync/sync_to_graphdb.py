"""
Minimal sync: StockShark rule engine output -> GraphDB triples.
Run as scheduled job (Airflow/Dagster/cron) every 5-15 min.
"""
import os
import json
from datetime import datetime
from typing import List, Dict
import requests

GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://localhost:7200")
REPO_ID = os.getenv("REPOSITORY_ID", "chan")
NAMED_GRAPH = os.getenv("NAMED_GRAPH", "http://d8q.com/graph/chan")

HEADERS = {"Content-Type": "application/x-turtle"}

# ---------- Prefixes ----------
PREFIXES = """
@prefix chan: <http://d8q.com/chan/> .
@prefix pe: <http://d8q.com/pe/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""

# ---------- Triple Builders ----------
def stroke_triples(symbol: str, level: str, s: Dict) -> str:
    """s = {id, start_time, end_time, high, low, start_price, end_price, direction}"""
    iri = f"chan:{symbol}_{level}_stroke_{s['id']}"
    start_iri = f"chan:{symbol}_{level}_fractal_{s['start_fractal_id']}"
    end_iri = f"chan:{symbol}_{level}_fractal_{s['end_fractal_id']}"
    return f"""
{iri} a chan:Stroke ;
    chan:hasLevel chan:{level} ;
    chan:hasStart {start_iri} ;
    chan:hasEnd {end_iri} ;
    chan:hasHigh "{s['high']}"^^xsd:decimal ;
    chan:hasLow "{s['low']}"^^xsd:decimal ;
    chan:hasSymbol pe:{symbol} .
{start_iri} a chan:Fractal ; chan:pointTime "{s['start_time']}"^^xsd:dateTime ; chan:pointPrice "{s['start_price']}"^^xsd:decimal .
{end_iri} a chan:Fractal ; chan:pointTime "{s['end_time']}"^^xsd:dateTime ; chan:pointPrice "{s['end_price']}"^^xsd:decimal .
"""

def segment_triples(symbol: str, level: str, seg: Dict) -> str:
    """seg = {id, stroke_ids[]}"""
    iri = f"chan:{symbol}_{level}_segment_{seg['id']}"
    strokes = " ;\n    ".join(f"chan:consistsOf chan:{symbol}_{level}_stroke_{sid}" for sid in seg['stroke_ids'])
    return f"""
{iri} a chan:LineSegment ;
    chan:hasLevel chan:{level} ;
    {strokes} ;
    chan:hasSymbol pe:{symbol} .
"""

def center_triples(symbol: str, level: str, c: Dict) -> str:
    """c = {id, zg, zd, gg, dd, segment_ids[]}"""
    iri = f"chan:{symbol}_{level}_center_{c['id']}"
    segs = " ;\n    ".join(f"chan:consistsOf chan:{symbol}_{level}_segment_{sid}" for sid in c['segment_ids'])
    return f"""
{iri} a chan:Center ;
    chan:hasLevel chan:{level} ;
    chan:hasZG "{c['zg']}"^^xsd:decimal ;
    chan:hasZD "{c['zd']}"^^xsd:decimal ;
    chan:hasGG "{c['gg']}"^^xsd:decimal ;
    chan:hasDD "{c['dd']}"^^xsd:decimal ;
    {segs} ;
    chan:hasSymbol pe:{symbol} .
"""

def buy_point_triples(symbol: str, bp: Dict) -> str:
    """bp = {id, type: 1/2/3, level, time, price, confirmed_by_id, confirmed_by_type: Center/LineSegment}"""
    iri = f"chan:{symbol}_{bp['level']}_buy_{bp['id']}"
    type_map = {1: "chan:Type1", 2: "chan:Type2", 3: "chan:Type3"}
    confirmed = f"chan:{symbol}_{bp['level']}_{bp['confirmed_by_type'].lower()}_{bp['confirmed_by_id']}"
    return f"""
{iri} a chan:BuyPoint ;
    chan:pointType {type_map[bp['type']]} ;
    chan:belongsToLevel chan:{bp['level']} ;
    chan:pointTime "{bp['time']}"^^xsd:dateTime ;
    chan:pointPrice "{bp['price']}"^^xsd:decimal ;
    chan:confirmedBy {confirmed} ;
    chan:hasSymbol pe:{symbol} .
"""

# ---------- Push ----------
def push_triples(turtle: str):
    r = requests.post(
        f"{GRAPHDB_URL}/repositories/{REPO_ID}/rdf-graphs/service?graph={NAMED_GRAPH}",
        headers=HEADERS,
        data=(PREFIXES + turtle).encode("utf-8")
    )
    r.raise_for_status()

# ---------- Public API ----------
def sync_symbol(symbol: str, level: str, strokes: List[Dict], segments: List[Dict], centers: List[Dict], buy_points: List[Dict]):
    """Call after rule engine finishes a symbol/level batch."""
    all_ttl = []
    for s in strokes:
        all_ttl.append(stroke_triples(symbol, level, s))
    for seg in segments:
        all_ttl.append(segment_triples(symbol, level, seg))
    for c in centers:
        all_ttl.append(center_triples(symbol, level, c))
    for bp in buy_points:
        all_ttl.append(buy_point_triples(symbol, bp))
    push_triples("\n".join(all_ttl))

# ---------- CLI test ----------
if __name__ == "__main__":
    # Example dummy data
    sync_symbol(
        "000001.SZ", "D",
        strokes=[{"id": 1, "start_fractal_id": 1, "end_fractal_id": 2, "high": 12.5, "low": 11.8,
                  "start_time": "2024-01-01T09:30:00", "end_time": "2024-01-02T15:00:00",
                  "start_price": 12.0, "end_price": 12.3}],
        segments=[{"id": 1, "stroke_ids": [1,2,3]}],
        centers=[{"id": 1, "zg": 12.5, "zd": 11.8, "gg": 12.4, "dd": 11.9, "segment_ids": [1,2,3]}],
        buy_points=[{"id": 1, "type": 1, "level": "D", "time": "2024-01-05T09:30:00", "price": 11.9,
                     "confirmed_by_id": 1, "confirmed_by_type": "Center"}]
    )
    print("✅ Test triples pushed")