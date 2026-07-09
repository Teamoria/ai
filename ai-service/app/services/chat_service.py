"""Chat session and message service."""

import logging
from urllib.parse import urlsplit

from app.core.database import get_session
from app.core.config import settings
from app.repositories.laravel_repository import LaravelRepository
from app.schemas.chat import (
    AiChatGenerateData,
    AiChatGenerateRequest,
    AiChatGenerateResponse,
    ChatRequest,
    ChatResponse,
    ChatSource,
)
from app.services.llm_service import LlmService
from app.services.rag_service import RagService


logger = logging.getLogger(__name__)


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


class AiChatGenerateService:
    """Laravel-ready AI chat generation over permission-filtered knowledge chunks."""

    def __init__(self, llm_service: LlmService | None = None) -> None:
        self.llm_service = llm_service or LlmService()

    def generate(self, request: AiChatGenerateRequest) -> AiChatGenerateResponse:
        chat_history = request.chat_history or []
        response_chat_history = request.chat_history or None
        casual_reply = self._casual_reply(request.message)
        if casual_reply is not None:
            return self._fallback_response(
                reply=casual_reply,
                chat_history=request.chat_history,
            )

        intent = self._intent(request.message)
        if intent == "general":
            return AiChatGenerateResponse(
                status="success",
                data=AiChatGenerateData(
                    reply=self.llm_service.answer_general_with_history(request.message, chat_history),
                    sources_used=[],
                    chat_history=response_chat_history,
                ),
            )

        try:
            with get_session() as session:
                repository = LaravelRepository(session)
                project_id = str(request.project_id) if request.project_id is not None else None
                if intent == "tasks":
                    identity = repository.ai_chat_identity_exists(
                        user_id=str(request.user_id),
                        company_id=str(request.company_id),
                    )
                    tasks = repository.ai_chat_visible_tasks(
                        user_id=str(request.user_id),
                        company_id=str(request.company_id),
                        project_id=project_id,
                    )
                    projects: list[dict] = []
                    uploads: list[dict] = []
                    chunks: list[dict] = []
                    summaries: list[dict] = []
                elif intent == "projects":
                    identity = repository.ai_chat_identity_exists(
                        user_id=str(request.user_id),
                        company_id=str(request.company_id),
                    )
                    projects = repository.ai_chat_visible_projects(
                        user_id=str(request.user_id),
                        company_id=str(request.company_id),
                        project_id=project_id,
                    )
                    tasks = []
                    uploads: list[dict] = []
                    chunks: list[dict] = []
                    summaries: list[dict] = []
                else:
                    identity = repository.ai_chat_identity_exists(
                        user_id=str(request.user_id),
                        company_id=str(request.company_id),
                    )
                    projects = []
                    tasks = []
                    uploads = repository.ai_chat_visible_uploads(
                        user_id=str(request.user_id),
                        company_id=str(request.company_id),
                        project_id=project_id,
                    )
                    upload_ids = [str(upload["id"]) for upload in uploads if upload.get("id")]
                    summaries = repository.ai_chat_meeting_summaries(upload_ids)
                    chunks = repository.ai_chat_knowledge_chunks(
                        user_id=str(request.user_id),
                        company_id=str(request.company_id),
                        project_id=project_id,
                    )
        except Exception as exc:
            logger.exception(
                "AI chat failed to read visible database context.",
                extra={
                    "ai_chat_intent": intent,
                    "ai_chat_user_id": str(request.user_id),
                    "ai_chat_company_id": str(request.company_id),
                    "ai_chat_project_id": project_id,
                    "database": self._database_diagnostic(),
                    "error_type": type(exc).__name__,
                },
            )
            return self._fallback_response(
                reply=(
                    "\u062a\u0639\u0630\u0631 \u0642\u0631\u0627\u0621\u0629 \u0628\u064a\u0627\u0646\u0627\u062a "
                    "\u0627\u0644\u0634\u0627\u062a \u0645\u0646 \u0642\u0627\u0639\u062f\u0629 "
                    "\u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u062d\u0627\u0644\u064a\u0627. "
                    "\u062a\u062d\u0642\u0642 \u0645\u0646 \u0644\u0648\u062c\u0627\u062a \u062e\u062f\u0645\u0629 "
                    "AI \u0644\u0645\u0639\u0631\u0641\u0629 \u0627\u0644\u0633\u0628\u0628."
                ),
                chat_history=request.chat_history,
            )

        sources_used = self._source_names(uploads, chunks)
        context = self._context(uploads, chunks, summaries)
        if intent == "tasks":
            context = self._task_context(tasks)
            sources_used = [str(task.get("title")) for task in tasks if task.get("title")]
        elif intent == "projects":
            context = self._project_context(projects)
            sources_used = [str(project.get("name")) for project in projects if project.get("name")]

        if not context:
            identity_reply = self._identity_problem_reply(identity, request)
            if identity_reply is not None:
                reply = identity_reply
            elif intent == "tasks":
                reply = self._empty_task_reply()
            elif intent == "projects":
                reply = self._empty_project_reply()
            else:
                reply = self._empty_context_reply()
        else:
            try:
                reply = self.llm_service.answer_with_history(
                    request.message,
                    context,
                    chat_history,
                )
            except Exception:
                logger.exception("AI chat failed to generate LLM reply.")
                reply = self._context_fallback_reply(intent, tasks, projects, uploads, chunks, summaries)

        return AiChatGenerateResponse(
            status="success",
            data=AiChatGenerateData(
                reply=reply,
                sources_used=sources_used,
                chat_history=response_chat_history,
            ),
        )

    def _context(self, uploads: list[dict], chunks: list[dict], summaries: list[dict] | None = None) -> str:
        parts: list[str] = []
        upload_context = self._upload_context(uploads)
        if upload_context:
            parts.append(upload_context)

        summary_context = self._summary_context(summaries or [])
        if summary_context:
            parts.append(summary_context)

        chunk_context = self._chunk_context(chunks)
        if chunk_context:
            parts.append(chunk_context)

        return "\n\n".join(parts)

    def _task_context(self, tasks: list[dict]) -> str:
        if not tasks:
            return ""

        lines = ["Visible tasks, ordered by due date or latest update:"]
        for index, task in enumerate(tasks, start=1):
            details = [
                f"{index}. Task: {task.get('title')}",
                f"Task ID: {task.get('id')}",
                f"Project: {task.get('project_name') or ''}",
                f"Project ID: {task.get('project_id') or ''}",
                f"Status: {task.get('status') or ''}",
                f"Priority: {task.get('priority') or ''}",
                f"Due date: {task.get('due_date') or ''}",
                f"Access: {task.get('access_reason') or 'visible'}",
                f"Description: {task.get('description') or ''}",
            ]
            lines.append("\n".join(details))

        return "\n\n".join(lines)

    def _project_context(self, projects: list[dict]) -> str:
        if not projects:
            return ""

        lines = [f"Visible projects count: {len(projects)}", "Visible projects:"]
        for index, project in enumerate(projects, start=1):
            details = [
                f"{index}. Project: {project.get('name')}",
                f"Project ID: {project.get('id')}",
                f"Status: {project.get('status') or ''}",
                f"Progress: {project.get('progress') or 0}",
                f"Start date: {project.get('start_date') or ''}",
                f"End date: {project.get('end_date') or ''}",
                f"Access: {project.get('access_reason') or 'visible'}",
                f"Description: {project.get('description') or ''}",
            ]
            lines.append("\n".join(details))

        return "\n\n".join(lines)

    def _upload_context(self, uploads: list[dict]) -> str:
        if not uploads:
            return ""

        lines = ["Latest visible uploads, ordered newest first:"]
        for index, upload in enumerate(uploads, start=1):
            file_name = str(upload.get("file_name") or "unknown source")
            uploaded_at = upload.get("upload_date") or upload.get("updated_at") or ""
            project_id = upload.get("project_id") or ""
            access_reason = upload.get("access_reason") or "visible"
            details = [
                f"{index}. File: {file_name}",
                f"Upload ID: {upload.get('id')}",
                f"Uploaded at: {uploaded_at}",
                f"Access: {access_reason}",
                f"Status: {upload.get('status') or ''}",
                f"Type: {upload.get('file_type') or ''}",
                f"Category: {upload.get('category') or ''}",
                f"Scope: {upload.get('scope') or ''}",
                f"Visibility: {upload.get('visibility') or ''}",
            ]
            if project_id:
                details.append(f"Project ID: {project_id}")
            lines.append("\n".join(details))

        return "\n\n".join(lines)

    def _summary_context(self, summaries: list[dict]) -> str:
        if not summaries:
            return ""

        lines = ["Available processed file summaries, ordered newest first:"]
        for index, summary in enumerate(summaries, start=1):
            summary_text = str(summary.get("summary") or "").strip()
            transcript_text = str(summary.get("transcript") or "").strip()
            if not summary_text and not transcript_text:
                continue

            details = [
                f"{index}. File: {summary.get('file_name') or 'unknown source'}",
                f"Upload ID: {summary.get('upload_id')}",
                f"Updated at: {summary.get('updated_at') or summary.get('upload_updated_at') or ''}",
            ]
            if summary_text:
                details.append(f"Summary: {summary_text}")
            elif transcript_text:
                details.append(f"Transcript excerpt: {transcript_text[:2000]}")
            lines.append("\n".join(details))

        return "\n\n".join(lines) if len(lines) > 1 else ""

    def _chunk_context(self, chunks: list[dict]) -> str:
        parts: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            content = str(chunk.get("content") or "").strip()
            if not content:
                continue

            file_name = str(chunk.get("file_name") or "unknown source")
            project_id = chunk.get("upload_project_id") or chunk.get("project_id") or ""
            uploaded_at = chunk.get("upload_date") or chunk.get("upload_updated_at") or chunk.get("updated_at") or ""
            metadata = [
                f"Processed source {index}: {file_name}",
                f"Uploaded at: {uploaded_at}",
            ]
            if project_id:
                metadata.append(f"Project ID: {project_id}")

            metadata_text = "\n".join(metadata)
            parts.append(f"{metadata_text}\nContent:\n{content}")

        return "\n\n".join(parts)

    def _empty_context_reply(self) -> str:
        return (
            "\u0644\u0627 \u0623\u0633\u062a\u0637\u064a\u0639 \u0627\u0644\u0639\u062b\u0648\u0631 "
            "\u0639\u0644\u0649 \u0645\u0644\u0641\u0627\u062a \u0645\u0639\u0631\u0641\u0629 "
            "\u0645\u062a\u0627\u062d\u0629 \u0644\u0647\u0630\u0627 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645 "
            "\u062f\u0627\u062e\u0644 \u0627\u0644\u0634\u0631\u0643\u0629 \u062d\u0627\u0644\u064a\u0627. "
            "\u062a\u0623\u0643\u062f \u0645\u0646 \u0648\u062c\u0648\u062f \u0645\u0644\u0641\u0627\u062a "
            "\u0645\u0639\u0627\u0644\u062c\u0629 \u0623\u0648 \u0635\u0644\u0627\u062d\u064a\u0627\u062a "
            "\u0648\u0635\u0648\u0644 \u0645\u0646\u0627\u0633\u0628\u0629."
        )

    def _empty_task_reply(self) -> str:
        return (
            "لا أستطيع العثور على مهام متاحة لهذا المستخدم حالياً. "
            "تأكد من أن المستخدم عضو في المشروع أو أن المهام مسندة له."
        )

    def _empty_project_reply(self) -> str:
        return (
            "لا أستطيع العثور على مشاريع متاحة لهذا المستخدم حالياً. "
            "تأكد من أن المستخدم تابع للشركة أو مضاف على المشاريع."
        )

    def _context_fallback_reply(
        self,
        intent: str,
        tasks: list[dict],
        projects: list[dict],
        uploads: list[dict],
        chunks: list[dict],
        summaries: list[dict] | None = None,
    ) -> str:
        if intent == "tasks" and tasks:
            lines = [f"وجدت {len(tasks)} مهام متاحة:"]
            for task in tasks[:10]:
                title = task.get("title") or "بدون عنوان"
                status = task.get("status") or "غير محدد"
                priority = task.get("priority") or "غير محددة"
                project_name = task.get("project_name") or "بدون مشروع"
                lines.append(f"- {title} | الحالة: {status} | الأولوية: {priority} | المشروع: {project_name}")
            return "\n".join(lines)

        if intent == "projects" and projects:
            lines = [f"عندك {len(projects)} مشاريع متاحة:"]
            for project in projects[:10]:
                name = project.get("name") or "بدون اسم"
                status = project.get("status") or "غير محدد"
                progress = project.get("progress") or 0
                lines.append(f"- {name} | الحالة: {status} | التقدم: {progress}%")
            return "\n".join(lines)

        if intent == "files" and (uploads or chunks):
            summary_reply = self._summary_fallback_reply(summaries or [])
            if summary_reply:
                return summary_reply

            names = self._source_names(uploads, chunks)
            lines = [f"وجدت {len(names)} ملفات/مصادر متاحة:"]
            for name in names[:10]:
                lines.append(f"- {name}")
            return "\n".join(lines)

        return (
            "\u0642\u0631\u0623\u062a \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u0645\u062a\u0627\u062d\u0629\u060c "
            "\u0644\u0643\u0646 \u062a\u0639\u0630\u0631 \u062a\u0648\u0644\u064a\u062f \u0631\u062f "
            "\u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a "
            "\u062d\u0627\u0644\u064a\u0627. \u062c\u0631\u0628 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649."
        )

    def _summary_fallback_reply(self, summaries: list[dict]) -> str:
        for summary in summaries:
            file_name = str(summary.get("file_name") or "unknown source")
            summary_text = str(summary.get("summary") or "").strip()
            if summary_text:
                return f"آخر ملخص متاح للملف {file_name}:\n\n{summary_text}"

            transcript_text = str(summary.get("transcript") or "").strip()
            if transcript_text:
                return f"لا يوجد ملخص محفوظ للملف {file_name}، لكن هذا مقتطف من محتواه:\n\n{transcript_text[:2000]}"

        return ""

    def _identity_problem_reply(self, identity: dict[str, bool], request: AiChatGenerateRequest) -> str | None:
        if not identity["user_exists"] and not identity["company_exists"]:
            return (
                "لا أستطيع قراءة بيانات المستخدم لأن user_id و company_id المرسلة لا تطابق قاعدة البيانات. "
                f"وصلني user_id={request.user_id} و company_id={request.company_id}. "
                "أرسل UUID الحقيقي من Laravel auth user/company."
            )
        if not identity["user_exists"]:
            return (
                f"لا أستطيع قراءة بيانات المستخدم لأن user_id={request.user_id} غير موجود في قاعدة البيانات. "
                "أرسل UUID الحقيقي للمستخدم."
            )
        if not identity["company_exists"]:
            return (
                f"لا أستطيع قراءة بيانات الشركة لأن company_id={request.company_id} غير موجود في قاعدة البيانات. "
                "أرسل UUID الحقيقي للشركة."
            )
        if not identity["user_in_company"]:
            return (
                "المستخدم موجود والشركة موجودة، لكن المستخدم غير تابع لهذه الشركة حسب قاعدة البيانات. "
                "تحقق من company_id المرسل مع المستخدم الحالي."
            )

        return None

    def _casual_reply(self, message: str) -> str | None:
        normalized = self._normalized_message(message)
        repeated_chars_normalized = self._collapse_repeated_chars(normalized)

        greetings = {
            "الو",
            "الوو",
            "هلا",
            "اهلا",
            "أهلا",
            "مرحبا",
            "مراحب",
            "السلام عليكم",
            "hi",
            "hello",
            "hey",
        }
        if normalized in greetings or repeated_chars_normalized in greetings:
            return "أهلا، معك Teamoria AI. كيف أقدر أساعدك؟"

        return None

    def _intent(self, message: str) -> str:
        normalized = self._normalized_message(message)
        file_words = {
            "file",
            "files",
            "upload",
            "uploads",
            "document",
            "documents",
            "pdf",
            "ملف",
            "ملفات",
            "مرفق",
            "مرفقات",
            "مستند",
            "مستندات",
            "وثيقة",
            "وثائق",
            "رفع",
            "مرفوع",
            "المرفوعة",
        }
        task_words = {
            "task",
            "tasks",
            "todo",
            "todos",
            "assignment",
            "assignments",
            "مهمة",
            "مهام",
            "تاسك",
            "تاسكات",
            "واجب",
            "واجبات",
            "المهمام",
            "المهام",
            "مسند",
            "المسندة",
        }
        platform_words = {
            "teamoria",
            "project",
            "projects",
            "company",
            "workspace",
            "مشروع",
            "مشاريع",
            "شركة",
            "الشركة",
            "منصة",
            "تيموريا",
        }
        words = set(normalized.split())
        arabic_task_terms = {"مهمة", "مهام", "تاسك", "تاسكات", "واجب", "واجبات", "مسند"}
        arabic_file_terms = {"ملف", "ملفات", "مرفق", "مرفقات", "مستند", "مستندات", "وثيقة", "وثائق"}
        arabic_project_terms = {"مشروع", "مشاريع"}
        arabic_platform_terms = {"شركة", "منصة", "تيموريا", "داتا", "بيانات"}

        if words & task_words or any(term in normalized for term in arabic_task_terms):
            return "tasks"
        if any(term in normalized for term in arabic_project_terms) or words & {"project", "projects"}:
            return "projects"
        if words & file_words or any(term in normalized for term in arabic_file_terms):
            return "files"
        if words & platform_words or any(term in normalized for term in arabic_platform_terms):
            return "files"

        return "general"

    def _normalized_message(self, message: str) -> str:
        normalized = " ".join(message.strip().lower().split())
        return normalized.strip("؟?!.،,؛:()[]{}\"'")

    def _collapse_repeated_chars(self, message: str) -> str:
        return "".join(
            char
            for index, char in enumerate(message)
            if index == 0 or char != message[index - 1]
        )

    def _fallback_response(
        self,
        reply: str,
        chat_history: list | None,
    ) -> AiChatGenerateResponse:
        return AiChatGenerateResponse(
            status="success",
            data=AiChatGenerateData(
                reply=reply,
                sources_used=[],
                chat_history=chat_history or None,
            ),
        )

    def _source_names(self, uploads: list[dict], chunks: list[dict]) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        for item in [*uploads, *chunks]:
            name = str(item.get("file_name") or "").strip()
            if name and name not in seen:
                seen.add(name)
                names.append(name)

        return names

    def _database_diagnostic(self) -> dict[str, str]:
        try:
            parsed = urlsplit(settings.database_url)
        except Exception:
            return {"scheme": "invalid", "host": "", "database": ""}

        return {
            "scheme": parsed.scheme,
            "host": parsed.hostname or "",
            "database": parsed.path.lstrip("/").split("?", 1)[0],
        }
