import re
from typing import List, Tuple, Set
from app.schemas.chat import ChatResponse
from app.services.document_service import load_documents_for_role

# Stop words to ignore during keyword extraction
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "what", "on", "of", "and", "to", "for", "in", "at", "which", "how",
    "who", "where", "can", "tell", "me", "about", "show", "give", "please",
    "with", "by", "from", "it", "this", "that", "these", "those", "or"
}


def _split_into_chunks(text: str, max_chunk_len: int = 500) -> List[str]:
    """
    Splits text content into paragraph-based or line-based chunks for search granularity.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []

    for para in paragraphs:
        if len(para) <= max_chunk_len:
            chunks.append(para)
        else:
            lines = [line.strip() for line in para.split("\n") if line.strip()]
            current_chunk: List[str] = []
            current_len = 0
            for line in lines:
                if current_len + len(line) > max_chunk_len and current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                    current_len = len(line)
                else:
                    current_chunk.append(line)
                    current_len += len(line)
            if current_chunk:
                chunks.append("\n".join(current_chunk))

    return chunks if chunks else [text[:max_chunk_len]]


def search_documents(query: str, role: str) -> ChatResponse:
    """
    Searches permitted documents for the specified role using multi-term keyword matching and relevance scoring.
    Enforces minimum matching terms threshold so single coincidental words do not trigger false positive matches.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return ChatResponse(
            query=query,
            answer="Please enter a valid query message.",
            sources=[],
            role=role,
            status="no_results"
        )

    # 1. Load permitted documents for user role
    documents = load_documents_for_role(role)
    if not documents:
        return ChatResponse(
            query=query,
            answer="No documents are accessible for your role.",
            sources=[],
            role=role,
            status="no_results"
        )

    # 2. Extract meaningful search terms from user query (filtering stop words)
    raw_terms = re.findall(r"\w+", cleaned_query.lower())
    query_terms = [term for term in raw_terms if term not in STOP_WORDS and len(term) > 1]

    if not query_terms:
        query_terms = [t for t in raw_terms if len(t) > 1] or raw_terms

    # Minimum distinct terms required to count as a match
    # If query has 2+ meaningful terms, require at least 2 distinct terms in the chunk
    min_required_matches = min(2, len(query_terms))

    scored_snippets: List[Tuple[float, str, str]] = []  # (score, snippet, filename)

    # 3. Score document chunks based on multi-term matching & proximity
    for doc in documents:
        filename = doc["filename"]
        content = doc["content"]
        chunks = _split_into_chunks(content)

        for chunk in chunks:
            chunk_lower = chunk.lower()
            matched_terms_count = 0
            total_occurrences = 0

            for term in query_terms:
                matches = len(re.findall(rf"\b{re.escape(term)}\b", chunk_lower))
                if matches > 0:
                    matched_terms_count += 1
                    total_occurrences += matches

            # Enforce threshold: chunk must match at least min_required_matches distinct terms
            if matched_terms_count >= min_required_matches:
                # Score formula: Heavily weight distinct term count + total occurrences
                score = (matched_terms_count * 10.0) + (total_occurrences * 1.0)

                # Bonus if the full query phrase appears verbatim
                if cleaned_query.lower() in chunk_lower:
                    score += 15.0

                scored_snippets.append((score, chunk, filename))

    # 4. Sort snippets by relevance score descending
    scored_snippets.sort(key=lambda x: x[0], reverse=True)

    if not scored_snippets:
        return ChatResponse(
            query=query,
            answer="No relevant information found in your permitted documents.",
            sources=[],
            role=role,
            status="no_results"
        )

    # 5. Extract top excerpts and unique source list (top 3 max)
    top_snippets = scored_snippets[:3]
    matched_sources: Set[str] = set()
    formatted_excerpts: List[str] = []

    for idx, (score, snippet, source_file) in enumerate(top_snippets, start=1):
        matched_sources.add(source_file)
        display_snippet = snippet if len(snippet) <= 600 else snippet[:597] + "..."
        formatted_excerpts.append(f"[Excerpt {idx} from {source_file}]:\n{display_snippet}")

    answer_text = "\n\n".join(formatted_excerpts)

    return ChatResponse(
        query=query,
        answer=answer_text,
        sources=sorted(list(matched_sources)),
        role=role,
        status="success"
    )
