from typing import Dict, Any, List
from app.schemas.chat import ChatResponse
from app.services.llm_service import generate_llm_answer


def generate_answer(retrieval_result: Dict[str, Any]) -> ChatResponse:
    """
    Modular Answer Generation Service for Phase 2F.
    Produces a ChatResponse object from authorized RAG retrieval results.
    Tries Google Gemini API synthesis if GOOGLE_API_KEY is configured.
    Falls back gracefully to deterministic Offline Retrieval Fallback mode if API key is missing or fails.
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
            status="no_results",
            mode="offline_fallback"
        )

    # 2. No matching authorized chunks handling (Gemini is NOT called)
    if not chunks:
        return ChatResponse(
            query=query,
            answer="No relevant information was found in the authorized company documents.",
            sources=[],
            role=role,
            status="no_results",
            mode="offline_fallback"
        )

    # 3. Try Gemini LLM Answer Synthesis
    llm_answer = generate_llm_answer(query=query, chunks=chunks, sources=sources)
    if llm_answer:
        return ChatResponse(
            query=query,
            answer=llm_answer,
            sources=sources,
            role=role,
            status="success",
            mode="gemini"
        )

    # 4. Deterministic Offline Retrieval Fallback Mode (if Gemini is unconfigured/fails)
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
        status="success",
        mode="offline_fallback"
    )
