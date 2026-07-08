"""Document intelligence tests."""

from app.services.document_intelligence_service import DocumentIntelligenceService


def test_media_analysis_returns_estimated_speaker_segments() -> None:
    transcript = (
        "[00:00:00-00:01:00] Speaker 1: We reviewed the upload flow. "
        "[00:01:00-00:02:00] Speaker 2: Ahmad will update Laravel."
    )
    service = DocumentIntelligenceService()

    result = service.analyze(
        transcript,
        source_type="media",
        meeting_analysis={
            "summary": "Media summary",
            "decisions": [],
            "decision_items": [],
            "tasks": ["Ahmad will update Laravel"],
            "task_items": [],
            "transcript_quality": {"level": "high"},
        },
    )

    structured = result["structured_result"]
    assert structured["speaker_diarization_status"] == "estimated_from_timestamped_chunks"
    assert structured["speaker_segments"] == [
        {
            "speaker": "Speaker 1",
            "start": "00:00:00",
            "end": "00:01:00",
            "text": "Speaker 1: We reviewed the upload flow.",
        },
        {
            "speaker": "Speaker 2",
            "start": "00:01:00",
            "end": "00:02:00",
            "text": "Speaker 2: Ahmad will update Laravel.",
        },
    ]
