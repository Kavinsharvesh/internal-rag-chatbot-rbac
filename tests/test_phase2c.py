import sys
from pathlib import Path

# Ensure project root is in sys.path so imports work cleanly from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.document_service import load_all_chunks
from app.services.vector_service import (
    index_documents,
    query_vector_store,
    get_or_create_collection,
    CHROMA_DB_DIR
)


def test_phase2c_vector_store():
    print("==================================================")
    print(" RUNNING PHASE 2C VECTOR STORE & CHROMADB TEST ")
    print("==================================================")

    # 1. Verify document chunks source
    chunks = load_all_chunks()
    total_chunks = len(chunks)
    print(f"\n1. Loaded total raw document chunks: {total_chunks}")
    assert total_chunks > 0, "No chunks loaded from document service!"

    # 2. Perform initial indexing
    print("\n2. Indexing chunks into ChromaDB (First Run)...")
    indexed_count_1 = index_documents(reset=False)
    print(f"   Chunks indexed in ChromaDB: {indexed_count_1}")
    assert indexed_count_1 == total_chunks, f"Expected {total_chunks} chunks, got {indexed_count_1}"

    # 3. Verify local persistent directory creation
    print(f"\n3. Checking persistence directory: {CHROMA_DB_DIR}")
    assert CHROMA_DB_DIR.exists(), f"ChromaDB directory {CHROMA_DB_DIR} does not exist!"
    assert list(CHROMA_DB_DIR.iterdir()), f"ChromaDB directory {CHROMA_DB_DIR} is empty!"
    print("   PASSED: chroma_db/ directory exists and contains persistent files.")

    # 4. Perform simple similarity search test
    query_text = "architecture overview microservices"
    print(f"\n4. Executing sample similarity search for: '{query_text}'...")
    search_results = query_vector_store(query_text, n_results=2)

    metadatas = search_results.get("metadatas", [[]])[0]
    documents = search_results.get("documents", [[]])[0]
    distances = search_results.get("distances", [[]])[0] if "distances" in search_results else []

    assert len(metadatas) > 0, "Search returned no results!"
    print("   Search Results Returned:")
    for idx, meta in enumerate(metadatas, start=1):
        dist_info = f" (distance: {distances[idx-1]:.4f})" if idx - 1 < len(distances) else ""
        print(f"   [{idx}] Source: {meta.get('source')} | Dept: {meta.get('department')}{dist_info}")
        safe_snippet = documents[idx-1][:100].encode("ascii", errors="ignore").decode("ascii")
        print(f"       Snippet: {safe_snippet}...\n")


    # 5. Idempotency & Deduplication Test (Index a Second Time)
    print("5. Indexing chunks into ChromaDB a SECOND time to verify no duplicates...")
    indexed_count_2 = index_documents(reset=False)
    print(f"   Chunks count after 2nd indexing: {indexed_count_2}")
    assert indexed_count_2 == indexed_count_1, (
        f"Duplicate records created! First count: {indexed_count_1}, Second count: {indexed_count_2}"
    )
    print("   PASSED: Deduplication verified. Re-indexing produced 0 duplicate chunks.")

    print("\n==================================================")
    print(" ALL PHASE 2C VECTOR STORE TESTS PASSED! ")
    print("==================================================")


if __name__ == "__main__":
    test_phase2c_vector_store()
