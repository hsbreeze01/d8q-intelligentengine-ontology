"""
SPARQL query functions for Chan Theory structures.
Uses Oxigraph's built-in SPARQL engine.
"""
from pyoxigraph import Store, NamedNode
from typing import List, Dict, Any

GRAPH = "http://d8q.com/graph/chan"


def _results_to_list(results) -> List[Dict[str, Any]]:
    """
    Convert Oxigraph SPARQL results to list of dicts.
    pyoxigraph QuerySolution supports iteration (yields values in SELECT order)
    and index access (row[0], row[1], ...), but NOT string key access (row["var"]).
    """
    rows = []
    for row in results:
        d = {}
        # Iterate by index since pyoxigraph doesn't support string key access
        for i, val in enumerate(row):
            if val is not None:
                d[f"col{i}"] = val.value if hasattr(val, "value") else str(val)
        if d:
            rows.append(d)
    return rows


def _query_with_vars(store: Store, query: str, var_names: List[str]) -> List[Dict[str, Any]]:
    """
    Execute SPARQL query and map columns to named variables.
    var_names: list of variable names in SELECT order.
    """
    results = store.query(query)
    rows = []
    for row in results:
        d = {}
        for i, name in enumerate(var_names):
            val = row[i] if i < len(row) else None
            if val is not None:
                d[name] = val.value if hasattr(val, "value") else str(val)
        if d:
            rows.append(d)
    return rows


def get_structure(store: Store, symbol: str) -> List[Dict[str, Any]]:
    """
    Get full Chan Theory structure for a symbol across all levels.
    Returns: list of {type, id, level, high, low, zg, zd, gg, dd, startTime, endTime}
    """
    query = f"""
    PREFIX chan: <http://d8q.com/chan/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT ?type ?id ?level ?high ?low ?zg ?zd ?gg ?dd ?startTime ?endTime
    WHERE {{
        GRAPH <{GRAPH}> {{
            {{
                ?id a chan:Stroke ;
                    chan:hasLevel ?level ;
                    chan:strokeHigh ?high ;
                    chan:strokeLow ?low ;
                    chan:strokeStartTime ?startTime ;
                    chan:strokeEndTime ?endTime .
                BIND("Stroke" AS ?type)
            }} UNION {{
                ?id a chan:LineSegment ;
                    chan:hasLevel ?level .
                BIND("LineSegment" AS ?type)
            }} UNION {{
                ?id a chan:Center ;
                    chan:hasLevel ?level ;
                    chan:hasZG ?zg ;
                    chan:hasZD ?zd ;
                    chan:hasGG ?gg ;
                    chan:hasDD ?dd .
                BIND("Center" AS ?type)
            }}
            FILTER(STRSTARTS(STR(?id), "http://d8q.com/chan/{symbol}"))
        }}
    }}
    ORDER BY ?level ?type ?id
    """
    var_names = ["type", "id", "level", "high", "low", "zg", "zd", "gg", "dd", "startTime", "endTime"]
    return _query_with_vars(store, query, var_names)


def get_strokes(store: Store, symbol: str, level: str) -> List[Dict[str, Any]]:
    """Get all strokes for a given symbol and level."""
    query = f"""
    PREFIX chan: <http://d8q.com/chan/>

    SELECT ?id ?high ?low ?startTime ?endTime ?direction
    WHERE {{
        GRAPH <{GRAPH}> {{
            ?id a chan:Stroke ;
                chan:hasLevel chan:{level} ;
                chan:hasSymbol chan:{symbol} ;
                chan:strokeHigh ?high ;
                chan:strokeLow ?low ;
                chan:strokeStartTime ?startTime ;
                chan:strokeEndTime ?endTime ;
                chan:strokeDirection ?direction .
        }}
    }}
    ORDER BY ?startTime
    """
    var_names = ["id", "high", "low", "startTime", "endTime", "direction"]
    return _query_with_vars(store, query, var_names)


def get_centers(store: Store, symbol: str, level: str) -> List[Dict[str, Any]]:
    """Get all centers for a given symbol and level."""
    query = f"""
    PREFIX chan: <http://d8q.com/chan/>

    SELECT ?id ?zg ?zd ?gg ?dd
    WHERE {{
        GRAPH <{GRAPH}> {{
            ?id a chan:Center ;
                chan:hasLevel chan:{level} ;
                chan:hasSymbol chan:{symbol} ;
                chan:hasZG ?zg ;
                chan:hasZD ?zd ;
                chan:hasGG ?gg ;
                chan:hasDD ?dd .
        }}
    }}
    ORDER BY ?id
    """
    var_names = ["id", "zg", "zd", "gg", "dd"]
    return _query_with_vars(store, query, var_names)


def verify_buy_point(store: Store, symbol: str) -> List[Dict[str, Any]]:
    """
    Verify all buy points for a symbol.
    Returns: list of {id, type, level, time, price, confirmedBy, confirmedByType}
    """
    query = f"""
    PREFIX chan: <http://d8q.com/chan/>

    SELECT ?id ?type ?level ?time ?price ?confirmedBy ?confirmedByType
    WHERE {{
        GRAPH <{GRAPH}> {{
            ?id a chan:BuyPoint ;
                chan:pointType ?type ;
                chan:belongsToLevel ?level ;
                chan:pointTime ?time ;
                chan:pointPrice ?price ;
                chan:confirmedBy ?confirmedBy ;
                chan:hasSymbol chan:{symbol} .
            ?confirmedBy a ?confirmedByType .
        }}
    }}
    ORDER BY ?level ?time
    """
    var_names = ["id", "type", "level", "time", "price", "confirmedBy", "confirmedByType"]
    return _query_with_vars(store, query, var_names)


def explain_signal(store: Store, signal_iri: str) -> List[Dict[str, Any]]:
    """
    Explain a specific buy/sell point signal with its full evidence chain.
    signal_iri: full IRI like "http://d8q.com/chan/000001.SZ_D_buy_123"
    """
    query = f"""
    PREFIX chan: <http://d8q.com/chan/>

    SELECT ?pred ?obj
    WHERE {{
        GRAPH <{GRAPH}> {{
            <{signal_iri}> ?pred ?obj .
        }}
    }}
    """
    var_names = ["pred", "obj"]
    return _query_with_vars(store, query, var_names)


def get_multi_level_summary(store: Store, symbol: str) -> Dict[str, Any]:
    """
    Get a summary of all levels for a symbol.
    Returns: {level: {stroke_count, center_count}}
    """
    query = f"""
    PREFIX chan: <http://d8q.com/chan/>

    SELECT ?level (COUNT(DISTINCT ?stroke) AS ?strokeCount) (COUNT(DISTINCT ?center) AS ?centerCount)
    WHERE {{
        GRAPH <{GRAPH}> {{
            OPTIONAL {{
                ?stroke a chan:Stroke ;
                    chan:hasLevel ?level ;
                    chan:hasSymbol chan:{symbol} .
            }}
            OPTIONAL {{
                ?center a chan:Center ;
                    chan:hasLevel ?level ;
                    chan:hasSymbol chan:{symbol} .
            }}
        }}
    }}
    GROUP BY ?level
    """
    var_names = ["level", "strokeCount", "centerCount"]
    results = _query_with_vars(store, query, var_names)
    summary = {}
    for row in results:
        level = row["level"].split("/")[-1] if "/" in row["level"] else row["level"]
        summary[level] = {
            "stroke_count": int(row["strokeCount"]),
            "center_count": int(row["centerCount"]),
        }
    return summary