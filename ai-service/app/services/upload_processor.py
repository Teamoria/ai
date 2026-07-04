"""Meeting and file upload processing service."""

from app.schemas.upload import KnowledgeChunkResponse, ProcessUploadRequest, ProcessUploadResponse
from app.services.embedding_service import EmbeddingService
from app.services.media_transcription_service import MediaTranscriptionService
from app.services.meeting_intelligence_service import MeetingIntelligenceService
from app.services.pinecone_service import PineconeService
from app.services.upload_persistence_service import UploadPersistenceService
from app.utils.chunking import chunk_text
from app.utils.file_extractors import resolve_upload_source


class UploadProcessor:
    def __init__(
        self,
        meeting_intelligence_service: MeetingIntelligenceService | None = None,
        embedding_service: EmbeddingService | None = None,
        media_transcription_service: MediaTranscriptionService | None = None,
        pinecone_service: PineconeService | None = None,
        persistence_service: UploadPersistenceService | None = None,
    ) -> None:
        self.meeting_intelligence_service = meeting_intelligence_service or MeetingIntelligenceService()
        self.embedding_service = embedding_service or EmbeddingService()
        self.media_transcription_service = media_transcription_service or MediaTranscriptionService()
        self.pinecone_service = pinecone_service or PineconeService()
        self.persistence_service = persistence_service or UploadPersistenceService()

    def process(self, request: ProcessUploadRequest) -> ProcessUploadResponse:
        source = resolve_upload_source(
            content=request.content,
            file_path=request.file_path,
            file_url=request.file_url,
        )

        if source.source_type == "media":
            if source.path is None:
                raise ValueError("Media source is missing its path.")
            transcript = self.media_transcription_service.transcribe(source.path)
        else:
            transcript = source.text or ""

        analysis = self.meeting_intelligence_service.analyze(transcript)
        summary = str(analysis["summary"])
        decisions = list(analysis["decisions"])
        tasks = list(analysis["tasks"])
        chunks = [
            KnowledgeChunkResponse(
                content=chunk,
                embedding=self.embedding_service.embed(chunk),
                metadata={
                    "chunk_index": index,
                    "source": source.source,
                    "source_type": source.source_type,
                },
            )
            for index, chunk in enumerate(chunk_text(transcript))
        ]
        chunk_payloads = [chunk.model_dump() for chunk in chunks]
        indexed_chunk_count = self.pinecone_service.index_upload_chunks(
            upload_id=request.upload_id,
            project_id=request.project_id,
            chunks=chunk_payloads,
        )
        persisted = self.persistence_service.save_processing_result(
            upload_id=request.upload_id,
            project_id=request.project_id,
            source_type=source.source_type,
            transcript=transcript,
            summary=summary,
            decisions=decisions,
            tasks=tasks,
        )

        return ProcessUploadResponse(
            upload_id=request.upload_id,
            project_id=request.project_id,
            source_type=source.source_type,
            transcript=transcript,
            summary=summary,
            decisions=decisions,
            tasks=tasks,
            chunks=chunks,
            indexed_chunk_count=indexed_chunk_count,
            persisted=persisted,
        )
