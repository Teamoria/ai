"""Meeting summary, decision, and task extraction service."""

import re

from fastapi import HTTPException

from app.clients.groq_client import GroqLlmClient
from app.core.config import settings


class MeetingIntelligenceService:
    """Extract meeting intelligence from text without owning persistence."""

    def __init__(self, llm_client: GroqLlmClient | None = None) -> None:
        self.llm_client = llm_client or GroqLlmClient()

    def analyze(self, transcript: str) -> dict[str, list[str] | str]:
        if settings.llm_provider.lower() == "groq" and settings.groq_api_key:
            return self._analyze_with_groq(transcript)

        return {
            "summary": self.summarize(transcript),
            "decisions": self.extract_decisions(transcript),
            "tasks": self.extract_tasks(transcript),
        }

    def summarize(self, transcript: str) -> str:
        sentences = self._sentences(transcript)

        if not sentences:
            return ""

        decisions = self.extract_decisions(transcript)
        tasks = self.extract_tasks(transcript)
        neutral_points = [
            sentence
            for sentence in sentences
            if sentence not in decisions and sentence not in tasks
        ]
        parts: list[str] = []

        if neutral_points:
            parts.append(f"Main discussion: {' '.join(neutral_points[:2])}")

        if decisions:
            parts.append(f"Key decision: {decisions[0]}")

        if tasks:
            parts.append(f"Next action: {tasks[0]}")

        if parts:
            return " ".join(parts)

        return " ".join(sentences[:2])

    def extract_decisions(self, transcript: str) -> list[str]:
        decisions: list[str] = []

        for sentence in self._sentences(transcript):
            lower_sentence = sentence.lower()

            if any(marker in lower_sentence for marker in ["decided", "decision", "agreed", "approved"]):
                decisions.append(sentence)

        return decisions[:10]

    def extract_tasks(self, transcript: str) -> list[str]:
        tasks: list[str] = []

        for sentence in self._sentences(transcript):
            lower_sentence = sentence.lower()

            if any(marker in lower_sentence for marker in ["todo", "task", "action item", "follow up", "will"]):
                tasks.append(sentence)

        return tasks[:10]

    def _sentences(self, text: str) -> list[str]:
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
            if sentence.strip()
        ]

    def _analyze_with_groq(self, transcript: str) -> dict[str, list[str] | str]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You extract meeting intelligence for a project-management backend. "
                    "Return only JSON with keys: summary, decisions, tasks. "
                    "summary must be a concise paragraph. decisions and tasks must be arrays of strings. "
                    "Use only the transcript."
                ),
            },
            {
                "role": "user",
                "content": transcript[:24000],
            },
        ]

        try:
            result = self.llm_client.complete_json(messages)
        except HTTPException:
            raise

        summary = result.get("summary") or ""
        decisions = result.get("decisions") or []
        tasks = result.get("tasks") or []

        return {
            "summary": str(summary),
            "decisions": [str(item) for item in decisions if str(item).strip()][:10],
            "tasks": [str(item) for item in tasks if str(item).strip()][:10],
        }
