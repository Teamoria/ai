"""Text chunking helpers."""


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    """Split text into overlapping chunks suitable for embeddings/RAG."""

    normalized_text = " ".join(text.split())

    if normalized_text == "":
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(normalized_text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(normalized_text[start:end])

        if end == text_length:
            break

        start = max(end - overlap, start + 1)

    return chunks
