"""Embedding creation service."""

import hashlib

from app.core.config import settings


class EmbeddingService:
    """Generate production embeddings when configured, with local fallback."""

    def embed(self, text: str, dimensions: int | None = None) -> list[float]:
        vector_size = dimensions or settings.embedding_dimensions

        if settings.embedding_provider.lower() == "openai" and settings.openai_api_key:
            return self._embed_with_openai(text, vector_size)

        return self._embed_locally(text, vector_size)

    def _embed_with_openai(self, text: str, vector_size: int) -> list[float]:
        try:
            from openai import OpenAI
        except ImportError:
            return self._embed_locally(text, vector_size)

        try:
            client = OpenAI(api_key=settings.openai_api_key)
            response = client.embeddings.create(
                model=settings.embedding_model,
                input=text,
                dimensions=vector_size,
            )
            values = list(response.data[0].embedding)
        except Exception:
            return self._embed_locally(text, vector_size)

        return _fit_vector_dimensions(values, vector_size)

    def _embed_locally(self, text: str, vector_size: int) -> list[float]:
        seed = text.encode("utf-8")
        values: list[float] = []
        block_index = 0

        while len(values) < vector_size:
            digest = hashlib.sha256(seed + str(block_index).encode("ascii")).digest()
            values.extend(round((byte / 255) * 2 - 1, 6) for byte in digest)
            block_index += 1

        return values[:vector_size]


def _fit_vector_dimensions(values: list[float], dimension: int) -> list[float]:
    if len(values) == dimension:
        return values
    if len(values) > dimension:
        return values[:dimension]
    return [*values, *([0.0] * (dimension - len(values)))]
