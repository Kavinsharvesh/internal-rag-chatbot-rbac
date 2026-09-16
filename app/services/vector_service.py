from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
from app.services.document_service import load_all_chunks

# Directory path where persistent ChromaDB data will be stored
CHROMA_DB_DIR = Path(__file__).resolve().parent.parent.parent / "chroma_db"
COLLECTION_NAME = "internal_knowledge_base"

# Initialize sentence-transformers embedding function with all-MiniLM-L6-v2
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


def get_chroma_client() -> chromadb.PersistentClient:
    """
    Returns a persistent ChromaDB client referencing chroma_db/ directory.
    """
    CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DB_DIR))


def get_or_create_collection():
    """
    Gets or creates the ChromaDB collection using sentence-transformers embedding function.
    """
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )


def index_documents(reset: bool = False) -> int:
    """
    Indexes all document chunks from resources/data/ into persistent ChromaDB.
    Uses upsert with deterministic chunk_id so repeated calls are reproducible and
    do NOT create duplicate records.
    """
    collection = get_or_create_collection()

    if reset:
        client = get_chroma_client()
        client.delete_collection(COLLECTION_NAME)
        collection = get_or_create_collection()

    chunks = load_all_chunks()
    if not chunks:
        return collection.count()

    ids = [c["chunk_id"] for c in chunks]
    documents = [c["content"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Process in batches of 100 for safe and efficient insertion
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_docs = documents[i : i + batch_size]
        batch_metadatas = metadatas[i : i + batch_size]

        collection.upsert(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metadatas
        )

    return collection.count()


def query_vector_store(
    query: str,
    n_results: int = 3,
    where_filter: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Queries ChromaDB vector collection with optional metadata filter.
    """
    collection = get_or_create_collection()
    kwargs: Dict[str, Any] = {
        "query_texts": [query],
        "n_results": n_results
    }
    if where_filter:
        kwargs["where"] = where_filter

    return collection.query(**kwargs)
