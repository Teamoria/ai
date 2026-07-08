"""Media transcription service tests."""

from pathlib import Path

from app.core.config import settings
from app.services.media_transcription_service import MediaTranscriptionService


class FakeWhisperClient:
    def __init__(self) -> None:
        self.languages: list[str | None] = []

    def transcribe_audio_file(self, audio_path: Path, *, language: str | None = None) -> str:
        self.languages.append(language)
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

    whisper_client = FakeWhisperClient()
    service = MediaTranscriptionService(whisper_client=whisper_client)
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


def test_media_transcription_passes_requested_language(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "media_chunk_seconds", 60)

    first_chunk = tmp_path / "chunk_0000.mp3"
    first_chunk.write_bytes(b"fake")

    whisper_client = FakeWhisperClient()
    service = MediaTranscriptionService(whisper_client=whisper_client)
    monkeypatch.setattr(service, "_resolve_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(
        service,
        "_extract_audio_chunks",
        lambda *, ffmpeg_path, media_path, output_dir: [first_chunk],
    )

    service.transcribe(tmp_path / "arabic-meeting.mp4", language="ar")

    assert whisper_client.languages == ["ar"]


def test_media_transcription_auto_detects_when_language_is_blank(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "media_chunk_seconds", 60)
    monkeypatch.setattr(settings, "groq_transcription_language", "")

    first_chunk = tmp_path / "chunk_0000.mp3"
    first_chunk.write_bytes(b"fake")

    whisper_client = FakeWhisperClient()
    service = MediaTranscriptionService(whisper_client=whisper_client)
    monkeypatch.setattr(service, "_resolve_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(
        service,
        "_extract_audio_chunks",
        lambda *, ffmpeg_path, media_path, output_dir: [first_chunk],
    )

    service.transcribe(tmp_path / "arabic-meeting.mp4")

    assert whisper_client.languages == [None]


def test_media_transcription_allows_english_language(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "media_chunk_seconds", 60)
    monkeypatch.setattr(settings, "groq_transcription_allowed_languages", "ar,en")

    first_chunk = tmp_path / "chunk_0000.mp3"
    first_chunk.write_bytes(b"fake")

    whisper_client = FakeWhisperClient()
    service = MediaTranscriptionService(whisper_client=whisper_client)
    monkeypatch.setattr(service, "_resolve_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(
        service,
        "_extract_audio_chunks",
        lambda *, ffmpeg_path, media_path, output_dir: [first_chunk],
    )

    service.transcribe(tmp_path / "english-meeting.mp4", language="en")

    assert whisper_client.languages == ["en"]


def test_media_transcription_rejects_unallowed_language(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "media_chunk_seconds", 60)
    monkeypatch.setattr(settings, "groq_transcription_allowed_languages", "ar,en")

    first_chunk = tmp_path / "chunk_0000.mp3"
    first_chunk.write_bytes(b"fake")

    whisper_client = FakeWhisperClient()
    service = MediaTranscriptionService(whisper_client=whisper_client)
    monkeypatch.setattr(service, "_resolve_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(
        service,
        "_extract_audio_chunks",
        lambda *, ffmpeg_path, media_path, output_dir: [first_chunk],
    )

    service.transcribe(tmp_path / "meeting.mp4", language="fr")

    assert whisper_client.languages == ["ar"]
