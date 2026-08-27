"""
Configuration for d8q-intelligentengine-ontology
"""
from pathlib import Path

BASE_DIR = Path(__file__).parent
ONTOLOGY_DIR = BASE_DIR / "ontology"
NAMED_GRAPH = "http://d8q.com/graph/chan"
ONTOLOGY_IRI = "http://d8q.com/ontology/chan"

# Oxigraph persistent storage
STORE_PATH = Path("/var/lib/d8q-ontology/store")

# SPARQL endpoint path
SPARQL_PATH = "/sparql"

# Server
HOST = "0.0.0.0"
PORT = 8080