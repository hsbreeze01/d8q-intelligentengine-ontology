"""
Tests for SPARQL query functions.
"""
import pytest
from pyoxigraph import Store
from sync.ingest import ingest
from sparql.chan_queries import (
    get_structure, get_strokes, get_centers,
    verify_buy_point, explain_signal, get_multi_level_summary
)


@pytest.fixture
def populated_store():
    """Store with test data loaded."""
    store = Store()
    ingest(store, "000001.SZ", "D",
           strokes=[
               {"id": 1, "start_fractal_id": 1, "end_fractal_id": 2,
                "high": 12.5, "low": 11.8,
                "start_time": "2024-01-01T09:30:00", "end_time": "2024-01-02T15:00:00",
                "direction": "up"},
               {"id": 2, "start_fractal_id": 2, "end_fractal_id": 3,
                "high": 13.0, "low": 12.0,
                "start_time": "2024-01-02T15:00:00", "end_time": "2024-01-03T15:00:00",
                "direction": "down"},
           ],
           centers=[
               {"id": 1, "zg": 12.5, "zd": 11.8, "gg": 12.4, "dd": 11.9, "segment_ids": [1, 2]},
           ],
           buy_points=[
               {"id": 1, "type": 1, "level": "D", "time": "2024-01-05T09:30:00",
                "price": 11.9, "confirmed_by_id": 1, "confirmed_by_type": "Center"},
           ])
    return store


def test_get_structure(populated_store):
    results = get_structure(populated_store, "000001.SZ")
    assert len(results) >= 3  # 2 strokes + 1 center
    types = {r["type"] for r in results}
    assert "Stroke" in types
    assert "Center" in types


def test_get_strokes(populated_store):
    results = get_strokes(populated_store, "000001.SZ", "D")
    assert len(results) == 2


def test_get_centers(populated_store):
    results = get_centers(populated_store, "000001.SZ", "D")
    assert len(results) == 1
    assert results[0]["zg"] == "12.5"


def test_verify_buy_point(populated_store):
    results = verify_buy_point(populated_store, "000001.SZ")
    assert len(results) == 1
    assert "Type1" in results[0]["type"]


def test_explain_signal(populated_store):
    signal_iri = "http://d8q.com/chan/000001.SZ_D_buy_1"
    results = explain_signal(populated_store, signal_iri)
    assert len(results) > 0
    preds = {r["pred"] for r in results}
    assert any("pointType" in p for p in preds)


def test_get_multi_level_summary(populated_store):
    summary = get_multi_level_summary(populated_store, "000001.SZ")
    assert "D" in summary
    assert summary["D"]["stroke_count"] == 2
    assert summary["D"]["center_count"] == 1