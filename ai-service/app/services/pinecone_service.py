"""Pinecone vector database service."""

from app.core.config import settings
from app.services.embedding_service import EmbeddingService


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

        try:
            _enable_system_certificates()
            pc = Pinecone(api_key=settings.pinecone_api_key)
            index = pc.Index(host=settings.pinecone_host) if settings.pinecone_host else pc.Index(index_name)
        except Exception:
            return 0

        namespace = settings.pinecone_namespace or f"{settings.pinecone_namespace_prefix}-{project_id or 'global'}"
        dimension = _resolve_index_dimension(pc, index_name)

        vectors = [
            {
                "id": f"{upload_id}-{chunk['metadata']['chunk_index']}",
                "values": _fit_vector_dimensions(chunk["embedding"], dimension),
                "metadata": _pinecone_metadata(
                    {
                        **chunk["metadata"],
                        "upload_id": upload_id,
                        "project_id": project_id,
                        "text": chunk["content"],
                    }
                ),
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

    def search_chunks(
        self,
        *,
        project_id: str,
        company_id: str | None = None,
        scope: str | None = None,
        visibility: str | None = None,
        question: str,
        top_k: int = 5,
    ) -> list[dict]:
        index_name = settings.pinecone_index_name or settings.pinecone_index
        if not settings.pinecone_api_key or not index_name:
            return []

        try:
            from pinecone import Pinecone
        except ImportError:
            return []

        try:
            _enable_system_certificates()
            pc = Pinecone(api_key=settings.pinecone_api_key)
            index = pc.Index(host=settings.pinecone_host) if settings.pinecone_host else pc.Index(index_name)
            dimension = _resolve_index_dimension(pc, index_name)
            query_vector = _fit_vector_dimensions(EmbeddingService().embed(question), dimension)
            namespace = settings.pinecone_namespace or f"{settings.pinecone_namespace_prefix}-{project_id or 'global'}"
            result = index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=_search_filter(
                    project_id=project_id,
                    company_id=company_id,
                    scope=scope,
                    visibility=visibility,
                ),
                include_metadata=True,
            )
        except Exception:
            return []

        matches = result.get("matches", []) if isinstance(result, dict) else getattr(result, "matches", [])
        sources: list[dict] = []
        for match in matches:
            metadata = _match_value(match, "metadata", {}) or {}
            sources.append(
                {
                    "content": metadata.get("text") or metadata.get("content") or "",
                    "score": _match_value(match, "score", None),
                    "metadata": _source_metadata(metadata),
                }
            )
        return sources


def _enable_system_certificates() -> None:
    try:
        import truststore
    except ImportError:
        return

    try:
        truststore.inject_into_ssl()
    except Exception:
        return


def _pinecone_metadata(metadata: dict) -> dict:
    return {
        key: value
        for key, value in metadata.items()
        if value is not None
    }


def _search_filter(
    *,
    project_id: str,
    company_id: str | None,
    scope: str | None,
    visibility: str | None,
) -> dict:
    filters: list[dict] = [{"project_id": {"$eq": project_id}}]
    if company_id:
        filters.append({"company_id": {"$eq": company_id}})
    if scope:
        filters.append({"scope": {"$eq": scope}})
    if visibility:
        filters.append({"visibility": {"$eq": visibility}})
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


def _source_metadata(metadata: dict) -> dict:
    content = str(metadata.get("text") or metadata.get("content") or "")
    chunk_index = metadata.get("chunk_index")
    upload_id = metadata.get("upload_id")
    source_id = f"{upload_id}:{chunk_index}" if upload_id is not None and chunk_index is not None else upload_id
    return {
        **metadata,
        "source_id": source_id,
        "snippet": content[:500],
    }


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


def _match_value(match, key: str, default):
    if isinstance(match, dict):
        return match.get(key, default)
    return getattr(match, key, default)
