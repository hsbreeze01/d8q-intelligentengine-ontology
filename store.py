"""
Oxigraph store manager - singleton store instance.
"""
from pathlib import Path
from pyoxigraph import Store, NamedNode
from config import ONTOLOGY_DIR, STORE_PATH, NAMED_GRAPH

_store: Store | None = None


def get_store() -> Store:
    """Get or create the Oxigraph store, loading ontology files on first access."""
    global _store
    if _store is not None:
        return _store

    STORE_PATH.mkdir(parents=True, exist_ok=True)
    _store = Store(str(STORE_PATH))

    # Load TTL files
    for ttl_file in sorted(ONTOLOGY_DIR.glob("*.ttl")):
        print(f"[store] Loading {ttl_file.name}")
        _store.load_file(str(ttl_file), format="text/turtle")

    print(f"[store] Ontology loaded. Triples: {len(_store)}")
    return _store


def reload_ontology():
    """Force reload all TTL files into the store."""
    global _store
    _store = None
    return get_store()