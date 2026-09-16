import sys
from pathlib import Path

# Add project root directory to sys.path so imports work cleanly from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.document_service import load_all_chunks


def test_chunking():
    chunks = load_all_chunks()
    print(f"Total chunks generated across resources/data/: {len(chunks)}")
    assert len(chunks) > 0, "No chunks loaded!"

    # Sample chunk inspection
    first_chunk = chunks[0]
    print("\n--- First Chunk Example ---")
    print(f"ID: {first_chunk['chunk_id']}")
    print(f"Metadata: {first_chunk['metadata']}")
    print(f"Content Snippet: {first_chunk['content'][:150]}...\n")

    # Check required metadata fields on all chunks
    required_keys = {"department", "source", "filename", "chunk_id"}
    for idx, c in enumerate(chunks):
        assert required_keys.issubset(c["metadata"].keys()), f"Missing metadata keys in chunk {idx}"

    # Check sensitive HR fields (salary) protection
    hr_chunks = [c for c in chunks if c["metadata"]["department"] == "hr"]
    print(f"Total HR chunks: {len(hr_chunks)}")
    for c in hr_chunks:
        assert "salary:" not in c["content"].lower(), "Salary exposed in HR chunk!"

    print("PASSED: Phase 2B Chunking and Metadata Verification Successful!")


if __name__ == "__main__":
    test_chunking()
