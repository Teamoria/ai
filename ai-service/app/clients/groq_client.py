"""Groq API client wrappers."""

from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


class GroqWhisperClient:
    """Transcribe audio files through Groq Whisper."""

    def transcribe_audio_file(self, audio_path: Path) -> str:
        if not settings.groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GROQ_API_KEY is required to transcribe audio or video uploads.",
            )

        try:
            from groq import Groq
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Install the groq package to enable audio transcription.",
            ) from exc

        client = Groq(
            api_key=settings.groq_api_key,
            http_client=httpx.Client(verify=settings.groq_verify_ssl, timeout=settings.groq_request_timeout),
        )

        try:
            with audio_path.open("rb") as audio_file:
                payload: dict[str, Any] = {
                    "file": (audio_path.name, audio_file.read()),
                    "model": settings.groq_transcription_model,
                    "response_format": "text",
                }
                if settings.groq_transcription_language:
                    payload["language"] = settings.groq_transcription_language
                if settings.groq_transcription_prompt:
                    payload["prompt"] = settings.groq_transcription_prompt
                result = client.audio.transcriptions.create(**payload)
        except Exception as exc:  # pragma: no cover - provider/network dependent
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Groq transcription failed: {exc}",
            ) from exc

        return str(result).strip()


class GroqLlmClient:
    """Generate structured meeting intelligence through Groq chat completions."""

    def complete_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        if not settings.groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GROQ_API_KEY is required to run Groq LLM intelligence.",
            )

        try:
            from groq import Groq
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Install the groq package to enable Groq LLM calls.",
            ) from exc

        client = Groq(
            api_key=settings.groq_api_key,
            http_client=httpx.Client(verify=settings.groq_verify_ssl, timeout=settings.groq_request_timeout),
        )

        try:
            completion = client.chat.completions.create(
                model=settings.groq_llm_model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # pragma: no cover - provider/network dependent
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Groq LLM request failed: {exc}",
            ) from exc

        content = completion.choices[0].message.content or "{}"

        import json

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Groq LLM returned invalid JSON.",
            ) from exc
