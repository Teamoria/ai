"""Media transcription service tests."""

from pathlib import Path

from app.core.config import settings
from app.services.media_transcription_service import MediaTranscriptionService


class FakeWhisperClient:
    def transcribe_audio_file(self, audio_path: Path) -> str:
        if audio_path.name == "chunk_0000.mp3":
            return "Hello team. Hello team. We discussed the upload flow."
        return "Ahmad will review the Laravel job. Ahmad will review the Laravel job."


def test_media_transcription_adds_timestamps_and_removes_repeated_sentences(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "media_chunk_seconds", 60)

    first_chunk = tmp_path / "chunk_0000.mp3"
    second_chunk = tmp_path / "chunk_0001.mp3"
    first_chunk.write_bytes(b"fake")
    second_chunk.write_bytes(b"fake")

    service = MediaTranscriptionService(whisper_client=FakeWhisperClient())
    monkeypatch.setattr(service, "_resolve_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(
        service,
        "_extract_audio_chunks",
        lambda *, ffmpeg_path, media_path, output_dir: [first_chunk, second_chunk],
    )

    transcript = service.transcribe(tmp_path / "meeting.mp4")

    assert "[00:00:00-00:01:00] Hello team. We discussed the upload flow." in transcript
    assert "[00:01:00-00:02:00] Ahmad will review the Laravel job." in transcript
    assert transcript.count("Hello team.") == 1
    assert transcript.count("Ahmad will review the Laravel job.") == 1
