import re
from typing import List, Dict, Any, Set
from app.services.rbac_service import get_permitted_folders
from app.services.vector_service import query_vector_store

# Generic structural / modifier stop words to exclude when identifying key domain concepts
GENERIC_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "what", "on", "of", "and", "to", "for", "in", "at", "which", "how",
    "who", "where", "can", "tell", "me", "about", "show", "give", "please",
    "with", "by", "from", "it", "this", "that", "these", "those", "or",
    "quarterly", "report", "reports", "daily", "monthly", "annual", "document",
    "documents", "file", "files", "information", "data", "summary"
}


def _extract_domain_terms(query: str) -> List[str]:
    """
    Extracts core domain terms from user query by stripping generic stop words and structural modifiers.
    """
    raw_tokens = re.findall(r"\w+", query.lower())
    domain_terms = [t for t in raw_tokens if t not in GENERIC_STOP_WORDS and len(t) > 1]
    if not domain_terms:
        stop_words = {"the", "a", "an", "is", "are", "of", "on", "for", "and", "to", "in", "at"}
        domain_terms = [t for t in raw_tokens if t not in stop_words and len(t) > 1] or raw_tokens
    return domain_terms


def retrieve_authorized_chunks(
    query: str,
    role: str,
    n_results: int = 3,
    distance_threshold: float = 0.75
) -> Dict[str, Any]:
    """
    RAG Retrieval Engine with Backend Pre-Filtering RBAC Enforcement and Relevance Validation.

    SECURITY ARCHITECTURE:
    1. Resolves permitted departments for the user's role via rbac_service.
    2. Constructs ChromaDB metadata filter: where={"department": {"$in": permitted_departments}}
    3. Passes filter directly into ChromaDB vector query BEFORE similarity search.
    4. Validates vector results against distance threshold (0.75) and key domain term presence.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return {
            "query": query,
            "role": role,
            "permitted_departments": [],
            "where_filter": {},
            "chunks": [],
            "sources": [],
            "status": "no_results",
            "message": "Query string is empty."
        }

    # 1. Determine permitted department folders for user role
    permitted_departments = get_permitted_folders(role)

    # 2. Build ChromaDB pre-filtering metadata query
    if len(permitted_departments) == 1:
        where_filter = {"department": permitted_departments[0]}
    else:
        where_filter = {"department": {"$in": permitted_departments}}

    # 3. Perform pre-filtered vector similarity search in ChromaDB
    raw_results = query_vector_store(
        query=cleaned_query,
        n_results=n_results,
        where_filter=where_filter
    )

    metadatas_list = raw_results.get("metadatas", [[]])[0]
    documents_list = raw_results.get("documents", [[]])[0]
    distances_list = raw_results.get("distances", [[]])[0] if "distances" in raw_results else []

    # Extract domain terms for hybrid lexical relevance validation
    domain_terms = _extract_domain_terms(cleaned_query)

    retrieved_chunks: List[Dict[str, Any]] = []
    matched_sources: Set[str] = set()

    for idx, (meta, doc) in enumerate(zip(metadatas_list, documents_list)):
        dist = distances_list[idx] if idx < len(distances_list) else None
        doc_lower = doc.lower()

        # 4a. Distance threshold validation (ChromaDB cosine distance)
        if dist is not None and dist > distance_threshold:
            continue

        # 4b. Key domain term overlap check to prevent generic word false positives
        if domain_terms:
            has_domain_match = any(
                re.search(rf"\b{re.escape(term)}\b", doc_lower) for term in domain_terms
            )
            if not has_domain_match:
                continue

        chunk_info = {
            "chunk_id": meta.get("chunk_id", ""),
            "content": doc,
            "source": meta.get("source", ""),
            "filename": meta.get("filename", ""),
            "department": meta.get("department", ""),
            "distance": dist
        }
        retrieved_chunks.append(chunk_info)
        if meta.get("source"):
            matched_sources.add(meta["source"])

    status = "success" if retrieved_chunks else "no_results"
    message = (
        f"Found {len(retrieved_chunks)} relevant authorized chunks."
        if retrieved_chunks
        else "No relevant authorized documents found."
    )

    return {
        "query": cleaned_query,
        "role": role,
        "permitted_departments": permitted_departments,
        "where_filter": where_filter,
        "chunks": retrieved_chunks,
        "sources": sorted(list(matched_sources)),
        "status": status,
        "message": message
    }
