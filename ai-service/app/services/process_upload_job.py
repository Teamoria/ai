"""Background upload processing job."""

from fastapi import HTTPException

from app.schemas.upload import ProcessUploadRequest
from app.services.upload_management_service import UploadManagementService
from app.services.upload_processor import UploadProcessor


class ProcessUploadJob:
    def __init__(
        self,
        upload_id: str,
        *,
        processor: UploadProcessor | None = None,
    ) -> None:
        self.upload_id = upload_id
        self.processor = processor or UploadProcessor()

    def run(self) -> None:
        service = UploadManagementService()

        try:
            upload = service.get_upload(self.upload_id, actor=_system_actor(), require_manage=True)
            upload_id = upload.id
            project_id = str(upload.project_id or "")
            file_path = upload.file_path
            service.set_status(upload_id, "processing")
            service.session.close()

            result = self.processor.process(
                ProcessUploadRequest(
                    upload_id=upload_id,
                    project_id=project_id,
                    file_path=file_path,
                ),
            )

            save_service = UploadManagementService()
            fresh_upload = save_service.get_upload(upload_id, actor=_system_actor(), require_manage=True)
            save_service.save_processing_result(
                upload=fresh_upload,
                source_type=result.source_type,
                transcript=result.transcript,
                summary=result.summary,
                decisions=result.decisions,
                tasks=result.tasks,
                chunks=[chunk.model_dump() for chunk in result.chunks],
            )
            save_service.session.close()
        except HTTPException as exc:
            _mark_failed(self.upload_id, str(exc.detail))
        except Exception as exc:  # pragma: no cover - defensive background safety
            _mark_failed(self.upload_id, str(exc))
        finally:
            service.session.close()


def _system_actor():
    from app.schemas.upload import UploadActor

    return UploadActor(user_id="system", role="admin")


def _mark_failed(upload_id: str, error: str) -> None:
    service = UploadManagementService()
    try:
        service.session.rollback()
        service.set_status(upload_id, "failed", error)
    finally:
        service.session.close()
