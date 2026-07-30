#!/usr/bin/env python3
"""
Bulk load TTL files into GraphDB repository on container startup.
Run once via docker-compose command or as init container.
"""
import os
import time
import requests
from pathlib import Path

GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://graphdb:7200")
REPO_ID = os.getenv("REPOSITORY_ID", "chan")
NAMED_GRAPH = os.getenv("NAMED_GRAPH", "http://d8q.com/graph/chan")
ONTOLOGY_DIR = Path("/app/ontology")

HEADERS_TTL = {"Content-Type": "application/x-turtle"}
HEADERS_JSON = {"Content-Type": "application/json"}

def wait_graphdb():
    """Wait until GraphDB REST API is responsive."""
    for _ in range(30):
        try:
            r = requests.get(f"{GRAPHDB_URL}/rest/repositories", timeout=5)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("GraphDB not ready after 60s")

def ensure_repository():
    """Create repository if not exists (uses built-in 'chan' config)."""
    # Check
    r = requests.get(f"{GRAPHDB_URL}/rest/repositories/{REPO_ID}")
    if r.status_code == 200:
        print(f"Repository '{REPO_ID}' already exists")
        return
    # Create from embedded config (GraphDB 10+ supports JSON config)
    config = {
        "id": REPO_ID,
        "title": "Chan Theory Repository",
        "type": "free",
        "params": {
            "ruleset": "owl-horst-optimized",
            "enable-context-index": "true",
            "enablePredicateList": "true",
            "enable-literal-index": "true"
        }
    }
    r = requests.post(
        f"{GRAPHDB_URL}/rest/repositories",
        headers=HEADERS_JSON,
        json=config
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Create repo failed: {r.status_code} {r.text}")
    print(f"Repository '{REPO_ID}' created")

def load_ttl_files():
    """Load all .ttl files in ontology dir into the named graph."""
    files = sorted(ONTOLOGY_DIR.glob("*.ttl"))
    if not files:
        print("No .ttl files found")
        return
    for f in files:
        print(f"Loading {f.name} -> {NAMED_GRAPH}")
        data = f.read_bytes()
        r = requests.post(
            f"{GRAPHDB_URL}/repositories/{REPO_ID}/rdf-graphs/service?graph={NAMED_GRAPH}",
            headers=HEADERS_TTL,
            data=data
        )
        if r.status_code not in (200, 201, 204):
            raise RuntimeError(f"Load {f.name} failed: {r.status_code} {r.text}")
    print(f"Loaded {len(files)} files into {NAMED_GRAPH}")

def main():
    wait_graphdb()
    ensure_repository()
    load_ttl_files()
    print("✅ Ontology bootstrap complete")

if __name__ == "__main__":
    main()