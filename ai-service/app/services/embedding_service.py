"""Embedding creation service."""

import hashlib

from app.core.config import settings


class EmbeddingService:
    """Generate deterministic embeddings for local/dev use."""

    def embed(self, text: str, dimensions: int | None = None) -> list[float]:
        vector_size = dimensions or settings.embedding_dimensions
        seed = text.encode("utf-8")
        values: list[float] = []
        block_index = 0

        while len(values) < vector_size:
            digest = hashlib.sha256(seed + str(block_index).encode("ascii")).digest()
            values.extend(round((byte / 255) * 2 - 1, 6) for byte in digest)
            block_index += 1

        return values[:vector_size]
