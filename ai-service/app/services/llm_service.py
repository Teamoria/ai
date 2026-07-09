"""LLM adapter for chat answers."""

from __future__ import annotations

from app.schemas.chat import ChatHistoryMessage
from openai import OpenAI

from app.core.config import settings


class LlmService:
    """OpenAI chat completion wrapper with a graceful missing-key response."""

    def answer(self, question: str, context: str) -> str:
        return self.answer_with_history(question, context, [])

    def answer_general_with_history(
        self,
        question: str,
        chat_history: list[ChatHistoryMessage],
    ) -> str:
        if not settings.openai_api_key:
            return (
                "أقدر أساعدك في أسئلة عامة أو أسئلة عن Teamoria. "
                "اسألني عن المهام، الملفات، أو أي شيء تريد توضيحه."
            )

        client = OpenAI(api_key=settings.openai_api_key, timeout=30.0)
        history_messages = [
            {"role": item.role, "content": item.content}
            for item in chat_history[-10:]
        ]
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Teamoria AI. Answer normal conversation and general questions naturally. "
                        "Do not claim access to platform data unless context was provided by another tool. "
                        "Match the user's language."
                    ),
                },
                *history_messages,
                {"role": "user", "content": question},
            ],
            temperature=0.4,
        )
        return completion.choices[0].message.content or ""

    def answer_with_history(
        self,
        question: str,
        context: str,
        chat_history: list[ChatHistoryMessage],
    ) -> str:
        if not settings.openai_api_key:
            return (
                "AI is configured correctly, but OPENAI_API_KEY is missing on the AI service. "
                "Please add OPENAI_API_KEY and OPENAI_MODEL, then restart the service."
            )

        client = OpenAI(api_key=settings.openai_api_key, timeout=30.0)
        history_messages = [
            {"role": item.role, "content": item.content}
            for item in chat_history[-10:]
        ]
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Teamoria AI. Answer only from the provided platform context. "
                        "Use source metadata such as file name, upload date, project ID, and project name "
                        "when the user asks about uploaded files or the latest company/project documents. "
                        "Use the latest visible uploads section to answer questions about the newest files, "
                        "shared files, upload status, file type, and file ownership. "
                        "Use processed knowledge chunks to explain file contents. "
                        "If the context is insufficient, say so clearly. Match the user's language."
                    ),
                },
                *history_messages,
                {
                    "role": "user",
                    "content": f"Question:\n{question}\n\nPlatform context:\n{context}",
                },
            ],
            temperature=0.2,
        )
        return completion.choices[0].message.content or ""
