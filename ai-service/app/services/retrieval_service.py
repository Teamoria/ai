"""Vector retrieval service for project knowledge chunks."""

from app.schemas.chat import RetrievalQueryRequest, RetrievalQueryResponse, RetrievalSource
from app.services.llm_service import LlmService
from app.services.pinecone_service import PineconeService


class RetrievalService:
    def __init__(
        self,
        pinecone_service: PineconeService | None = None,
        llm_service: LlmService | None = None,
    ) -> None:
        self.pinecone_service = pinecone_service or PineconeService()
        self.llm_service = llm_service or LlmService()

    def query(self, request: RetrievalQueryRequest) -> RetrievalQueryResponse:
        chunks = self.pinecone_service.search_chunks(
            project_id=request.project_id,
            company_id=request.company_id,
            scope=request.scope,
            visibility=request.visibility,
            question=request.question,
            top_k=request.top_k,
        )
        sources = [RetrievalSource(**chunk) for chunk in chunks if chunk.get("content")]
        context = "\n\n".join(source.content for source in sources)

        if not context:
            answer = (
                "No matching vector chunks were found for this project. "
                "Make sure the upload was processed and Pinecone indexing is configured."
            )
        else:
            answer = self.llm_service.answer(request.question, context)

        return RetrievalQueryResponse(
            project_id=request.project_id,
            question=request.question,
            answer=answer,
            sources=sources,
        )
