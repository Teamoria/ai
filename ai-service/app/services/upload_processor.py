"""Meeting and file upload processing service."""

from collections.abc import Callable

from app.schemas.upload import KnowledgeChunkResponse, ProcessUploadRequest, ProcessUploadResponse
from app.services.document_intelligence_service import DocumentIntelligenceService
from app.services.embedding_service import EmbeddingService
from app.services.media_transcription_service import MediaTranscriptionService
from app.services.meeting_intelligence_service import MeetingIntelligenceService
from app.services.pinecone_service import PineconeService
from app.utils.chunking import chunk_text
from app.utils.file_extractors import clean_extracted_text, resolve_upload_source


class UploadProcessor:
    def __init__(
        self,
        meeting_intelligence_service: MeetingIntelligenceService | None = None,
        document_intelligence_service: DocumentIntelligenceService | None = None,
        embedding_service: EmbeddingService | None = None,
        media_transcription_service: MediaTranscriptionService | None = None,
        pinecone_service: PineconeService | None = None,
    ) -> None:
        self.meeting_intelligence_service = meeting_intelligence_service or MeetingIntelligenceService()
        self.document_intelligence_service = document_intelligence_service or DocumentIntelligenceService()
        self.embedding_service = embedding_service or EmbeddingService()
        self.media_transcription_service = media_transcription_service or MediaTranscriptionService()
        self.pinecone_service = pinecone_service or PineconeService()

    def process(
        self,
        request: ProcessUploadRequest,
        *,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ProcessUploadResponse:
        project_id = request.project_id or ""

        def report(status_value: str) -> None:
            if progress_callback is not None:
                progress_callback(status_value)

        report("extracting")
        source = resolve_upload_source(
            content=request.content,
            file_path=request.file_path,
            file_url=request.file_url,
            file_url_headers=request.file_url_headers,
            file_url_api_key=request.file_url_api_key,
            file_url_bearer_token=request.file_url_bearer_token,
        )

        if source.source_type == "media":
            if source.path is None:
                raise ValueError("Media source is missing its path.")
            report("transcribing")
            transcript = clean_extracted_text(self.media_transcription_service.transcribe(source.path))
        else:
            transcript = clean_extracted_text(source.text or "")

        report("analyzing")
        analysis = self.meeting_intelligence_service.analyze(transcript)
        document_analysis = self.document_intelligence_service.analyze(
            transcript,
            source_type=source.source_type,
            meeting_analysis=analysis,
            job_description=request.job_description,
        )
        summary = str(document_analysis.get("summary") or analysis["summary"])
        transcript_quality = analysis.get("transcript_quality")
        decisions = list(analysis["decisions"])
        tasks = list(analysis["tasks"])
        structured_summary = analysis.get("structured_summary")
        decision_items = list(analysis.get("decision_items") or [])
        task_items = list(analysis.get("task_items") or [])
        document_type = str(document_analysis.get("document_type") or "document")
        if document_type not in {"meeting", "media"}:
            decisions = []
            decision_items = []
            tasks = []
            task_items = []
        report("chunking")
        base_metadata = {
            "upload_id": request.upload_id,
            "company_id": request.company_id,
            "project_id": project_id,
            "task_id": request.task_id,
            "scope": request.scope,
            "visibility": request.visibility,
            "source": source.source,
            "source_type": source.source_type,
            "document_type": document_type,
        }
        chunks = [
            KnowledgeChunkResponse(
                content=chunk,
                embedding=self.embedding_service.embed(chunk),
                metadata={
                    **base_metadata,
                    "chunk_index": index,
                },
            )
            for index, chunk in enumerate(chunk_text(transcript))
        ]
        chunk_payloads = [chunk.model_dump() for chunk in chunks]
        report("indexing")
        indexed_chunk_count = self.pinecone_service.index_upload_chunks(
            upload_id=request.upload_id,
            project_id=project_id,
            chunks=chunk_payloads,
        )
        report("saving")

        return ProcessUploadResponse(
            upload_id=request.upload_id,
            project_id=project_id,
            source_type=source.source_type,
            document_type=document_type,
            transcript=transcript,
            transcript_quality=transcript_quality if isinstance(transcript_quality, dict) else None,
            summary=summary,
            structured_summary=structured_summary if isinstance(structured_summary, dict) else None,
            structured_result=document_analysis.get("structured_result") or {},
            decisions=decisions,
            decision_items=decision_items,
            tasks=tasks,
            task_items=task_items,
            quality=document_analysis.get("quality") or {},
            warnings=list(document_analysis.get("warnings") or []),
            chunks=chunks,
            indexed_chunk_count=indexed_chunk_count,
            persisted=False,
        )
