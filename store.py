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

    # Only load TTL if store is empty (first run or after clear)
    if len(_store) == 0:
        for ttl_file in sorted(ONTOLOGY_DIR.glob("*.ttl")):
            print(f"[store] Loading {ttl_file.name}")
            _store.load(path=str(ttl_file), format="text/turtle")
        print(f"[store] Ontology loaded. Triples: {len(_store)}")
    else:
        print(f"[store] Store has {len(_store)} triples (persistent)")

    return _store


def reload_ontology():
    """Force reload all TTL files into the store."""
    global _store
    _store = None
    return get_store()