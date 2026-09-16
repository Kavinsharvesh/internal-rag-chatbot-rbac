from typing import Dict, Any, List
from app.schemas.chat import ChatResponse


def generate_answer(retrieval_result: Dict[str, Any]) -> ChatResponse:
    """
    Modular Answer Generation Service for Phase 2E.
    Formats authorized RAG retrieval results into a ChatResponse model.
    Implements the deterministic Offline Retrieval Fallback without external LLM dependencies.
    """
    query = retrieval_result.get("query", "")
    role = retrieval_result.get("role", "")
    chunks = retrieval_result.get("chunks", [])
    sources = retrieval_result.get("sources", [])

    # 1. Empty / invalid query handling
    if not query or not query.strip():
        return ChatResponse(
            query=query,
            answer="Please enter a valid query message.",
            sources=[],
            role=role,
            status="no_results"
        )

    # 2. No matching authorized chunks handling
    if not chunks:
        return ChatResponse(
            query=query,
            answer="No relevant information was found in the authorized company documents.",
            sources=[],
            role=role,
            status="no_results"
        )

    # 3. Format deterministic Offline Retrieval Fallback answer
    excerpt_lines: List[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        source_name = chunk.get("source", "unknown")
        content_snippet = chunk.get("content", "").strip()
        excerpt_lines.append(f"[Excerpt {idx} from {source_name}]:\n{content_snippet}")

    excerpts_body = "\n\n".join(excerpt_lines)
    answer_text = (
        "Offline retrieval fallback: I found relevant information in the authorized company documents.\n\n"
        f"Relevant excerpts:\n{excerpts_body}"
    )

    return ChatResponse(
        query=query,
        answer=answer_text,
        sources=sources,
        role=role,
        status="success"
    )
