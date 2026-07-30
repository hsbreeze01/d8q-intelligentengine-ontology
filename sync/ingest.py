"""
Ingest: Rule engine output -> Oxigraph triples.
Called by StockShark/DataFactory to push structure data into the knowledge graph.
"""
from pyoxigraph import Store, NamedNode, BlankNode, Literal, Quad
from typing import List, Dict, Any

# Namespace IRIs
CHAN = "http://d8q.com/chan/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XSD = "http://www.w3.org/2001/XMLSchema#"
GRAPH = "http://d8q.com/graph/chan"


def _node(iri: str) -> NamedNode:
    return NamedNode(iri)


def _lit(val: Any, dtype: str = f"{XSD}string") -> Literal:
    return Literal(str(val), datatype=NamedNode(dtype))


def _ingest_strokes(store: Store, symbol: str, level: str, strokes: List[Dict]):
    """Ingest stroke (笔) instances."""
    graph = _node(GRAPH)
    for s in strokes:
        sid = f"{CHAN}{symbol}_{level}_stroke_{s['id']}"
        start_id = f"{CHAN}{symbol}_{level}_fractal_{s.get('start_fractal_id', s['id'] * 10 + 1)}"
        end_id = f"{CHAN}{symbol}_{level}_fractal_{s.get('end_fractal_id', s['id'] * 10 + 2)}"

        triples = [
            # type
            Quad(_node(sid), _node(f"{RDF}type"), _node(f"{CHAN}Stroke"), graph),
            # level
            Quad(_node(sid), _node(f"{CHAN}hasLevel"), _node(f"{CHAN}{level}"), graph),
            # symbol
            Quad(_node(sid), _node(f"{CHAN}hasSymbol"), _node(f"{CHAN}{symbol}"), graph),
            # direction
            Quad(_node(sid), _node(f"{CHAN}strokeDirection"),
                 _node(f"{CHAN}{s['direction'].capitalize()}"), graph),
            # high / low
            Quad(_node(sid), _node(f"{CHAN}strokeHigh"), _lit(s['high'], f"{XSD}decimal"), graph),
            Quad(_node(sid), _node(f"{CHAN}strokeLow"), _lit(s['low'], f"{XSD}decimal"), graph),
            # start / end fractal
            Quad(_node(sid), _node(f"{CHAN}hasStart"), _node(start_id), graph),
            Quad(_node(sid), _node(f"{CHAN}hasEnd"), _node(end_id), graph),
            # start / end time
            Quad(_node(sid), _node(f"{CHAN}strokeStartTime"), _lit(s['start_time'], f"{XSD}dateTime"), graph),
            Quad(_node(sid), _node(f"{CHAN}strokeEndTime"), _lit(s['end_time'], f"{XSD}dateTime"), graph),
        ]
        for q in triples:
            store.add(q)


def _ingest_segments(store: Store, symbol: str, level: str, segments: List[Dict]):
    """Ingest line segment (线段) instances."""
    graph = _node(GRAPH)
    for seg in segments:
        sid = f"{CHAN}{symbol}_{level}_segment_{seg['id']}"
        quads = [
            Quad(_node(sid), _node(f"{RDF}type"), _node(f"{CHAN}LineSegment"), graph),
            Quad(_node(sid), _node(f"{CHAN}hasLevel"), _node(f"{CHAN}{level}"), graph),
            Quad(_node(sid), _node(f"{CHAN}hasSymbol"), _node(f"{CHAN}{symbol}"), graph),
        ]
        for stroke_id in seg.get("stroke_ids", []):
            stroke_iri = f"{CHAN}{symbol}_{level}_stroke_{stroke_id}"
            quads.append(Quad(_node(sid), _node(f"{CHAN}consistsOf"), _node(stroke_iri), graph))
        for q in quads:
            store.add(q)


def _ingest_centers(store: Store, symbol: str, level: str, centers: List[Dict]):
    """Ingest center (中枢) instances."""
    graph = _node(GRAPH)
    for c in centers:
        sid = f"{CHAN}{symbol}_{level}_center_{c['id']}"
        quads = [
            Quad(_node(sid), _node(f"{RDF}type"), _node(f"{CHAN}Center"), graph),
            Quad(_node(sid), _node(f"{CHAN}hasLevel"), _node(f"{CHAN}{level}"), graph),
            Quad(_node(sid), _node(f"{CHAN}hasSymbol"), _node(f"{CHAN}{symbol}"), graph),
            Quad(_node(sid), _node(f"{CHAN}hasZG"), _lit(c['zg'], f"{XSD}decimal"), graph),
            Quad(_node(sid), _node(f"{CHAN}hasZD"), _lit(c['zd'], f"{XSD}decimal"), graph),
            Quad(_node(sid), _node(f"{CHAN}hasGG"), _lit(c['gg'], f"{XSD}decimal"), graph),
            Quad(_node(sid), _node(f"{CHAN}hasDD"), _lit(c['dd'], f"{XSD}decimal"), graph),
        ]
        for seg_id in c.get("segment_ids", []):
            seg_iri = f"{CHAN}{symbol}_{level}_segment_{seg_id}"
            quads.append(Quad(_node(sid), _node(f"{CHAN}consistsOf"), _node(seg_iri), graph))
        for q in quads:
            store.add(q)


def _ingest_buy_points(store: Store, symbol: str, level: str, buy_points: List[Dict]):
    """Ingest buy point (买点) instances."""
    graph = _node(GRAPH)
    type_map = {1: "Type1", 2: "Type2", 3: "Type3"}
    for bp in buy_points:
        sid = f"{CHAN}{symbol}_{level}_buy_{bp['id']}"
        confirmed = f"{CHAN}{symbol}_{level}_{bp['confirmed_by_type'].lower()}_{bp['confirmed_by_id']}"
        quads = [
            Quad(_node(sid), _node(f"{RDF}type"), _node(f"{CHAN}BuyPoint"), graph),
            Quad(_node(sid), _node(f"{CHAN}pointType"), _node(f"{CHAN}{type_map[bp['type']]}"), graph),
            Quad(_node(sid), _node(f"{CHAN}belongsToLevel"), _node(f"{CHAN}{level}"), graph),
            Quad(_node(sid), _node(f"{CHAN}pointTime"), _lit(bp['time'], f"{XSD}dateTime"), graph),
            Quad(_node(sid), _node(f"{CHAN}pointPrice"), _lit(bp['price'], f"{XSD}decimal"), graph),
            Quad(_node(sid), _node(f"{CHAN}confirmedBy"), _node(confirmed), graph),
            Quad(_node(sid), _node(f"{CHAN}hasSymbol"), _node(f"{CHAN}{symbol}"), graph),
        ]
        for q in quads:
            store.add(q)


def ingest(
    store: Store,
    symbol: str,
    level: str,
    strokes: List[Dict] | None = None,
    segments: List[Dict] | None = None,
    centers: List[Dict] | None = None,
    buy_points: List[Dict] | None = None,
):
    """
    Ingest one symbol+level batch of Chan Theory structures into the store.
    Called by StockShark rule engine or DataFactory sync.
    """
    if strokes:
        _ingest_strokes(store, symbol, level, strokes)
    if segments:
        _ingest_segments(store, symbol, level, segments)
    if centers:
        _ingest_centers(store, symbol, level, centers)
    if buy_points:
        _ingest_buy_points(store, symbol, level, buy_points)

    total = sum([
        len(strokes or []),
        len(segments or []),
        len(centers or []),
        len(buy_points or []),
    ])
    return {"symbol": symbol, "level": level, "ingested": total}