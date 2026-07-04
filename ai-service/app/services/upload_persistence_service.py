"""Persistence hook for upload processing results."""

from app.core.database import get_session


class UploadPersistenceService:
    """Persist processing metadata when database wiring is available."""

    def save_processing_result(
        self,
        *,
        upload_id: str,
        project_id: str,
        source_type: str,
        transcript: str,
        summary: str,
        decisions: list[str],
        tasks: list[str],
    ) -> bool:
        try:
            session = get_session()
        except RuntimeError:
            return False

        # The approved ERD tables are owned by the PHP backend. Until migrations
        # for AI-owned persistence are added, this hook verifies DB availability
        # without inventing unapproved tables.
        session.close()
        return False
