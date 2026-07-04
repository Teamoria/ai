"""Embedding creation service."""

import hashlib


class EmbeddingService:
    """Generate small deterministic embeddings for local/dev use."""

    def embed(self, text: str, dimensions: int = 16) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()

        return [
            round((digest[index] / 255) * 2 - 1, 6)
            for index in range(min(dimensions, len(digest)))
        ]
