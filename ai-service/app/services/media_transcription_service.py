"""Media extraction, chunking, and transcription service."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException, status

from app.clients.groq_client import GroqWhisperClient
from app.core.config import settings


class MediaTranscriptionService:
    """Convert audio/video files into text using ffmpeg and Groq Whisper."""

    def __init__(self, whisper_client: GroqWhisperClient | None = None) -> None:
        self.whisper_client = whisper_client or GroqWhisperClient()

    def transcribe(self, media_path: Path) -> str:
        if not settings.groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GROQ_API_KEY is required to transcribe audio or video uploads.",
            )

        ffmpeg_path = self._resolve_ffmpeg()

        with tempfile.TemporaryDirectory(prefix="teamoria_media_") as temp_dir:
            chunk_paths = self._extract_audio_chunks(
                ffmpeg_path=ffmpeg_path,
                media_path=media_path,
                output_dir=Path(temp_dir),
            )
            transcripts = [
                self.whisper_client.transcribe_audio_file(chunk_path)
                for chunk_path in chunk_paths
            ]

        return " ".join(part for part in transcripts if part).strip()

    def _resolve_ffmpeg(self) -> str:
        configured = settings.ffmpeg_path

        if Path(configured).exists():
            return configured

        discovered = shutil.which(configured)

        if discovered:
            return discovered

        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ffmpeg is required to process audio or video uploads. Install ffmpeg or imageio-ffmpeg.",
        )

    def _extract_audio_chunks(
        self,
        *,
        ffmpeg_path: str,
        media_path: Path,
        output_dir: Path,
    ) -> list[Path]:
        output_pattern = output_dir / "chunk_%04d.mp3"
        command = [
            ffmpeg_path,
            "-y",
            "-i",
            str(media_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "segment",
            "-segment_time",
            str(settings.media_chunk_seconds),
            "-reset_timestamps",
            "1",
            str(output_pattern),
        ]

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=max(settings.media_chunk_seconds * 2, 120),
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unable to extract audio from media upload: {exc}",
            ) from exc

        chunk_paths = sorted(output_dir.glob("chunk_*.mp3"))

        if not chunk_paths:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No audio chunks were extracted from the uploaded media.",
            )

        return chunk_paths
