"""LLM adapter for chat answers."""

from __future__ import annotations

from openai import OpenAI

from app.core.config import settings


class LlmService:
    """OpenAI chat completion wrapper with a graceful missing-key response."""

    def answer(self, question: str, context: str) -> str:
        if not settings.openai_api_key:
            return (
                "AI is configured correctly, but OPENAI_API_KEY is missing on the AI service. "
                "Please add OPENAI_API_KEY and OPENAI_MODEL, then restart the service."
            )

        client = OpenAI(api_key=settings.openai_api_key)
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Teamoria AI. Answer only from the provided platform context. "
                        "If the context is insufficient, say so clearly. Match the user's language."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question:\n{question}\n\nPlatform context:\n{context}",
                },
            ],
            temperature=0.2,
        )
        return completion.choices[0].message.content or ""
