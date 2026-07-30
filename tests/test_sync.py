"""
Tests for sync/ingest module.
"""
import pytest
from pyoxigraph import Store
from sync.ingest import ingest


@pytest.fixture
def store():
    """Create a fresh in-memory store for each test."""
    return Store()


def test_ingest_strokes(store):
    strokes = [
        {
            "id": 1,
            "start_fractal_id": 1,
            "end_fractal_id": 2,
            "high": 12.5,
            "low": 11.8,
            "start_time": "2024-01-01T09:30:00",
            "end_time": "2024-01-02T15:00:00",
            "direction": "up",
        }
    ]
    result = ingest(store, "000001.SZ", "D", strokes=strokes)
    assert result["ingested"] == 1
    assert len(store) > 0


def test_ingest_centers(store):
    centers = [
        {
            "id": 1,
            "zg": 12.5,
            "zd": 11.8,
            "gg": 12.4,
            "dd": 11.9,
            "segment_ids": [1, 2, 3],
        }
    ]
    result = ingest(store, "000001.SZ", "D", centers=centers)
    assert result["ingested"] == 1
    # Should have triples for center + 3 consistsOf
    # Note: Must use GRAPH clause since data is in named graph
    count_query = store.query("""
        PREFIX chan: <http://d8q.com/chan/>
        SELECT (COUNT(?s) AS ?cnt) WHERE {
            GRAPH <http://d8q.com/graph/chan> {
                ?s a chan:Center
            }
        }
    """)
    for row in count_query:
        # Access by index since pyoxigraph QuerySolution doesn't support string keys
        cnt_val = row[0]
        assert int(cnt_val.value) == 1


def test_ingest_buy_points(store):
    buy_points = [
        {
            "id": 1,
            "type": 1,
            "level": "D",
            "time": "2024-01-05T09:30:00",
            "price": 11.9,
            "confirmed_by_id": 1,
            "confirmed_by_type": "Center",
        }
    ]
    result = ingest(store, "000001.SZ", "D", buy_points=buy_points)
    assert result["ingested"] == 1


def test_ingest_full_batch(store):
    """Test a complete ingestion cycle."""
    strokes = [
        {"id": i, "start_fractal_id": i * 10, "end_fractal_id": i * 10 + 1,
         "high": 12.0 + i * 0.1, "low": 11.5 + i * 0.1,
         "start_time": f"2024-01-0{i + 1}T09:30:00",
         "end_time": f"2024-01-0{i + 1}T15:00:00",
         "direction": "up" if i % 2 == 0 else "down"}
        for i in range(1, 6)
    ]
    segments = [{"id": 1, "stroke_ids": [1, 2, 3]}]
    centers = [{"id": 1, "zg": 12.5, "zd": 11.8, "gg": 12.4, "dd": 11.9, "segment_ids": [1]}]
    buy_points = [
        {"id": 1, "type": 1, "level": "D", "time": "2024-01-05T09:30:00",
         "price": 11.9, "confirmed_by_id": 1, "confirmed_by_type": "Center"}
    ]

    result = ingest(store, "000001.SZ", "D",
                    strokes=strokes, segments=segments,
                    centers=centers, buy_points=buy_points)
    assert result["ingested"] == 8  # 5 strokes + 1 segment + 1 center + 1 buy_point
    assert len(store) > 0