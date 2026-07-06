"""Pinecone vector database service."""

from app.core.config import settings


class PineconeService:
    """Index processed chunks in Pinecone when configured."""

    def index_upload_chunks(
        self,
        *,
        upload_id: str,
        project_id: str,
        chunks: list[dict],
    ) -> int:
        index_name = settings.pinecone_index_name or settings.pinecone_index
        if not settings.pinecone_api_key or not index_name:
            return 0

        try:
            from pinecone import Pinecone
        except ImportError:
            return 0

        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(host=settings.pinecone_host) if settings.pinecone_host else pc.Index(index_name)
        namespace = settings.pinecone_namespace or f"{settings.pinecone_namespace_prefix}-{project_id or 'global'}"
        dimension = _resolve_index_dimension(pc, index_name)

        vectors = [
            {
                "id": f"{upload_id}-{chunk['metadata']['chunk_index']}",
                "values": _fit_vector_dimensions(chunk["embedding"], dimension),
                "metadata": {
                    **chunk["metadata"],
                    "upload_id": upload_id,
                    "project_id": project_id,
                    "text": chunk["content"],
                },
            }
            for chunk in chunks
            if chunk.get("embedding")
        ]

        if not vectors:
            return 0

        try:
            index.upsert(vectors=vectors, namespace=namespace)
        except Exception:
            return 0

        return len(vectors)


def _resolve_index_dimension(pc, index_name: str) -> int:
    try:
        description = pc.describe_index(index_name)
    except Exception:
        return settings.embedding_dimensions

    if isinstance(description, dict):
        return int(description.get("dimension") or settings.embedding_dimensions)

    return int(getattr(description, "dimension", None) or settings.embedding_dimensions)


def _fit_vector_dimensions(values: list[float], dimension: int) -> list[float]:
    if len(values) == dimension:
        return values
    if len(values) > dimension:
        return values[:dimension]
    return [*values, *([0.0] * (dimension - len(values)))]
