"""Chat session and message service."""

from app.core.database import get_session
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.services.rag_service import RagService


class ChatService:
    """Stateless project Q&A service."""

    def answer(self, request: ChatRequest) -> ChatResponse:
        if request.user is not None:
            with get_session() as session:
                answer, sources = RagService(session).answer(request)

            return ChatResponse(
                project_id=request.project_id,
                question=request.question or request.message or "",
                answer=answer,
                sources=sources,
            )

        sources = [
            ChatSource(content=context, metadata={"rank": index + 1})
            for index, context in enumerate(request.context[:5])
        ]
        context_text = " ".join(source.content for source in sources)

        if context_text:
            answer = f"Based on the project knowledge, {self._compact_answer(request.question, context_text)}"
        else:
            answer = (
                "I do not have project knowledge context in this request yet. "
                "Send relevant chunks from Laravel or call the upload processing endpoint first."
            )

        return ChatResponse(
            project_id=request.project_id,
            question=request.question,
            answer=answer,
            sources=sources,
        )

    def _compact_answer(self, question: str, context: str) -> str:
        context_preview = context[:600].strip()

        return f"the answer to '{question}' is most likely found in: {context_preview}"
