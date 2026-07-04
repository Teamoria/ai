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
        if not settings.pinecone_api_key or not settings.pinecone_index_name:
            return 0

        try:
            from pinecone import Pinecone
        except ImportError:
            return 0

        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(settings.pinecone_index_name)
        namespace = f"{settings.pinecone_namespace_prefix}-{project_id}"

        vectors = [
            {
                "id": f"{upload_id}-{chunk['metadata']['chunk_index']}",
                "values": chunk["embedding"],
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

        index.upsert(vectors=vectors, namespace=namespace)
        return len(vectors)
