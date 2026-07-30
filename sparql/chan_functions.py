"""
SPARQL Query Templates for ChanOntology.
All queries assume GraphDB endpoint with ChanOntology.ttl loaded.
"""
from typing import List, Dict, Any
import os
import requests

GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://localhost:7200")
REPO_ID = os.getenv("GRAPHDB_REPO", "d8q-chan")
NAMED_GRAPH = os.getenv("GRAPHDB_NAMED_GRAPH", "http://d8q.com/chan/data")

ENDPOINT = f"{GRAPHDB_URL}/repositories/{REPO_ID}"
HEADERS = {"Accept": "application/sparql-results+json"}

PREFIXES = """
PREFIX chan: <http://d8q.com/chan/>
PREFIX fibo-md: <https://spec.edmcouncil.org/fibo/MD/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

def sparql_query(template: str, **params) -> List[Dict[str, Any]]:
    """Execute parameterized SPARQL query."""
    query = PREFIXES + template.format(**params)
    r = requests.post(ENDPOINT, headers=HEADERS, data={"query": query})
    r.raise_for_status()
    return r.json()["results"]["bindings"]


# ---------- 1. Get Full Structure ----------
GET_STRUCTURE = """
SELECT ?obj ?type ?level ?id ?high ?low ?zg ?zd ?gg ?dd ?startTime ?endTime ?startPrice ?endPrice
WHERE {
    GRAPH <{named_graph}> {
        {
            SELECT ?obj WHERE {
                ?obj a ?t ;
                     chan:hasLevel ?l .
                FILTER(?t IN (chan:Stroke, chan:LineSegment, chan:Center))
                FILTER(STRSTARTS(STR(?obj), STR(chan:{symbol})))
            }
        }
        OPTIONAL { ?obj a ?type . }
        OPTIONAL { ?obj chan:hasLevel ?level . }
        OPTIONAL { ?obj chan:hasId ?id . }
        OPTIONAL { ?obj chan:hasHigh ?high . }
        OPTIONAL { ?obj chan:hasLow ?low . }
        OPTIONAL { ?obj chan:hasZG ?zg . }
        OPTIONAL { ?obj chan:hasZD ?zd . }
        OPTIONAL { ?obj chan:hasGG ?gg . }
        OPTIONAL { ?obj chan:hasDD ?dd . }
        OPTIONAL { ?obj chan:hasStartTime ?startTime . }
        OPTIONAL { ?obj chan:hasEndTime ?endTime . }
        OPTIONAL { ?obj chan:hasStartPrice ?startPrice . }
        OPTIONAL { ?obj chan:hasEndPrice ?endPrice . }
    }
}
ORDER BY ?level ?id
"""

# ---------- 2. Verify Buy Points ----------
VERIFY_BUY_POINT = """
SELECT ?bp ?bpType ?level ?confirmedBy ?confirmedByType ?confirmedByLevel ?time ?price
WHERE {
    GRAPH <{named_graph}> {
        ?bp a chan:BuyPoint ;
            chan:pointType ?bpType ;
            chan:belongsToLevel ?level ;
            chan:hasTime ?time ;
            chan:hasPrice ?price .
        OPTIONAL {
            ?bp chan:confirmedBy ?confirmedBy .
            ?confirmedBy a ?confirmedByType ;
                         chan:hasLevel ?confirmedByLevel .
        }
        FILTER(STRSTARTS(STR(?bp), STR(chan:{symbol})))
    }
}
ORDER BY ?level ?time
"""

# ---------- 3. Explain Signal (evidence chain) ----------
EXPLAIN_SIGNAL = """
SELECT ?bp ?bpType ?level ?time ?price
       ?confirmedBy ?confirmedByType ?confirmedByLevel ?confirmedByZG ?confirmedByZD
       ?strokes ?segments
WHERE {
    GRAPH <{named_graph}> {
        BIND(chan:{signalId} AS ?bp)
        ?bp a chan:BuyPoint ;
            chan:pointType ?bpType ;
            chan:belongsToLevel ?level ;
            chan:hasTime ?time ;
            chan:hasPrice ?price .
        OPTIONAL {
            ?bp chan:confirmedBy ?confirmedBy .
            ?confirmedBy a ?confirmedByType ;
                         chan:hasLevel ?confirmedByLevel .
            OPTIONAL { ?confirmedBy chan:hasZG ?confirmedByZG . }
            OPTIONAL { ?confirmedBy chan:hasZD ?confirmedByZD . }
        }
        # 穿透获取底层笔/线段
        OPTIONAL {
            ?confirmedBy chan:consistsOf* ?sub .
            ?sub a ?subType .
            FILTER(?subType IN (chan:Stroke, chan:LineSegment))
        }
    }
}
"""


# ---------- Helper: quick test ----------
if __name__ == "__main__":
    import json
    print(json.dumps(sparql_query(GET_STRUCTURE, symbol="000001.SZ", named_graph=NAMED_GRAPH), indent=2, ensure_ascii=False))