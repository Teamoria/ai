# ملخص ملفات مشروع Teamoria Backend / AI Service

هذا الملف يلخص محتوى المشروع الحالي بعد قراءة الملفات الموجودة في المستودع.

## الفكرة العامة

المشروع يحتوي على Backend workspace باسم Teamoria، وفيه مجلدان مرتبطان بالذكاء الاصطناعي:

- `ai/`: وثائق تصميم وقواعد AI insights والـ dashboard والـ risk/recommendation formats.
- `ai-service/`: كود خدمة FastAPI الداخلية التي تنفذ APIs وخدمات المعالجة.

الفكرة المعمارية الأساسية:

```text
React Frontend
  -> PHP Backend
  -> FastAPI AI Service
  -> Groq LLM / Groq Whisper / Pinecone / MCP tools
```

حسب الوثائق، الـ PHP Backend يبقى مسؤولاً عن المستخدمين، الصلاحيات، الشركات، المشاريع، الاجتماعات، المهام، وواجهات frontend. أما `ai-service` فهي خدمة داخلية يستدعيها الـ PHP Backend فقط عبر REST API ومفتاح داخلي.

## الحالة الحالية للكود

الكود الحالي هو skeleton عملي لخدمة FastAPI، وفيه تنفيذ لمسار upload processing الأساسي:

- تشغيل FastAPI مع health check.
- حماية endpoints بمفتاح داخلي `X-Internal-API-Key`.
- endpoint بسيط للمحادثة `/api/v1/chat`.
- endpoint لمعالجة upload نصي أو ملف أو URL: `/api/v1/uploads/process`.
- اكتشاف ملفات الصوت/الفيديو وتحويلها إلى نص عبر `ffmpeg` وGroq Whisper عند ضبط الإعدادات.
- قراءة ملفات نصية وPDF وDOCX.
- تحليل transcript عبر Groq LLM عند توفر `GROQ_API_KEY`.
- fallback محلي للتلخيص واستخراج القرارات والمهام عند عدم توفر Groq.
- استخراج قرارات بجمل تحتوي كلمات مثل `decided`, `decision`, `agreed`, `approved`, `will` في fallback المحلي.
- تقسيم النص إلى chunks.
- توليد embeddings حتمية صغيرة باستخدام SHA-256 لأغراض local/dev.
- اختبارات أساسية للـ chat والـ upload.

أجزاء كثيرة ما زالت placeholders أو ملفات توثيق فقط، خصوصاً models، agents، sources، workspace graph، RAG الحقيقي، وmigrations. Pinecone وDB موجودان كـ hooks: يتفعلان عند توفر الإعدادات والجداول المعتمدة.

## ملفات الجذر

### `README.md`

يوضح أن المستودع هو Backend workspace لـ Teamoria، وأن خدمة الذكاء الاصطناعي ستكون FastAPI داخلية يتصل بها PHP Backend. يذكر نطاق الخدمة: RAG chat، upload processing، meeting summaries، decisions، tasks، embeddings، Pinecone، agents، citations، confidence scores.

### `ai-algorithms-diagrams.md`

وثيقة موسعة برسومات Mermaid تشرح تصور خوارزميات AI:

- upload processing.
- transcription.
- summarization.
- task extraction.
- RAG chat.
- vector search.
- agent workflow.
- MCP tools.
- workspace graph.

ملاحظة مهمة: هذه الوثيقة تصف نظاماً أوسع من الكود الحالي، وفيها أسماء مثل `backend/app/services/...` غير موجودة بنفس الشكل في هذا المستودع الحالي.

### `ai-service-api.md`

يوثق API contract لنسخة demo أوسع، فيها login و JWT و endpoints مثل `/meetings/upload`, `/tasks`, `/chat/`.

ملاحظة: الكود الحالي في `ai-service` يستخدم internal API key وليس JWT، والـ endpoints الفعلية الحالية تحت `/api/v1` تختلف جزئياً عن هذه الوثيقة.

### `ai-service-flow.md`

يوضح flow عام للخدمة:

- upload يدخل إلى UploadProcessor.
- استخراج نص أو transcription.
- تلخيص OpenAI.
- حفظ في PostgreSQL.
- indexing في Pinecone.
- RAG chat يستخدم access scope و vector search.

ملاحظة: هذا أيضاً هدف/تصور أوسع من التنفيذ الحالي.

### `demo-script.md`

سكريبت عرض demo: تشغيل Docker، login، upload meeting source، review tasks، تجربة chatbot. يحتوي أيضاً أمثلة عربية لكنها ظاهرة بترميز غير سليم mojibake.

## مجلد `ai/`

هذا المجلد يحتوي وثائق تصميم للـ AI insights والداشبورد، وليس كود Python.

### `ai/AI_Insights_Data_Model.md`

يقترح شكل بيانات AI insights ويربطها بجداول ERD الحالية مثل:

- `company`
- `user`
- `project`
- `task`
- `meeting_summary`
- `extracted_decision`
- `upload`
- `knowledge_chunk`

ينبه إلى عدم اختراع أسماء جداول بديلة.

### `ai/AI_Processing_Workflow.md`

يوثق workflow كامل من upload إلى dashboard insights:

1. رفع ملف.
2. استخراج نص أو transcription.
3. تلخيص.
4. إنشاء meeting summary.
5. indexing للـ chunks.
6. استخراج tasks.
7. توليد insights وتوصيات.

### `ai/AI_Response_Format.md`

يعرف JSON موحد لاستجابات AI insights، مع حقول مثل:

- `success`
- `title`
- `type`
- `severity`
- `confidence_score`
- `description`
- `recommendation`
- `related_entity`
- `sources`

### `ai/Confidence_Score_Format.md`

يعرف confidence score من `0.00` إلى `1.00`:

- `0.00-0.39`: low.
- `0.40-0.74`: medium.
- `0.75-1.00`: high.

### `ai/Dashboard_Insight_Rules.md`

يوثق قواعد insights للداشبورد مثل:

- overdue task.
- inactive project.
- delayed project progress.
- missing task updates.
- high workload team member.
- failed upload or AI processing.

### `ai/Project_Metadata_Schema.md`

يعرف metadata للمشروع مثل:

- progress.
- status.
- priority.
- deadline.
- team size.
- overdue tasks count.
- completed tasks count.
- inactive days.
- risk level.

### `ai/Recommendation_Format.md`

يعرف شكل التوصية:

- `action_title`
- `reason`
- `priority`
- `suggested_owner`
- `related_project_id`
- `related_task_id`
- `expected_outcome`
- `due_by`

### `ai/Risk_Detection_Logic.md`

يوثق طريقة حساب risk للمهمة والمشروع باستخدام scoring rules، مثل التأخير، blocked status، priority، workload، وذكر blockers في الاجتماعات.

## مجلد `ai-service/`

هذا هو كود خدمة FastAPI.

مزود الـ LLM الافتراضي مضبوط في الإعدادات على Groq:

- `LLM_PROVIDER=groq`
- `GROQ_API_KEY`
- `GROQ_LLM_MODEL`
- `GROQ_TRANSCRIPTION_MODEL`

يبقى OpenAI موجوداً كإعداد اختياري/احتياطي في الملفات، لكن كلام المشروع الحالي يجب أن يعتبر Groq هو المزود الأساسي للـ LLM/transcription.

### `ai-service/README.md`

وصف قصير للخدمة: internal AI service للـ RAG chat، meeting intelligence، embeddings، agent workflows. يؤكد أن frontend لا يستدعيها مباشرة.

### `ai-service/AI_IMPLEMENTATION_STEPS.md`

خطة Sprint 1 كاملة. أهم ما فيها:

- فصل AI service عن PHP backend.
- استخدام internal API key.
- توحيد request/response shape.
- بناء folders: api, core, models, schemas, services, clients, utils, tests. لا توجد حاجة إلى seeds في النسخة الجاهزة.
- endpoints متوقعة للـ chat, uploads, sources, agents, workspace graph.
- ترتيب التنفيذ المقترح وتعريف Done.

### `ai-service/requirements.txt`

اعتمادات Python:

- `fastapi`
- `uvicorn[standard]`
- `pydantic`
- `pydantic-settings`
- `sqlalchemy`
- `psycopg`
- `alembic`
- `groq`
- `openai`
- `pinecone`
- `pytest`

### `ai-service/.env.example`

متغيرات البيئة:

- `DATABASE_URL`
- `INTERNAL_API_KEY`
- `LLM_PROVIDER`
- `GROQ_API_KEY`
- `GROQ_LLM_MODEL`
- `GROQ_TRANSCRIPTION_MODEL`
- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `PINECONE_INDEX_NAME`

## FastAPI entrypoint

### `ai-service/app/main.py`

ينشئ تطبيق FastAPI باسم `Teamoria AI Service`.

الموجود فعلياً:

- CORS للـ localhost ports `3000` و `5173`.
- health endpoint:

```text
GET /health
```

- تسجيل v1 router تحت:

```text
/api/v1
```

## API layer

### `ai-service/app/api/deps.py`

يعيد تصدير dependency الأمان:

- `validate_internal_api_key`

### `ai-service/app/api/v1/router.py`

يجمع routers التالية:

- chat.
- uploads.
- agents.
- sources.
- workspace graph.

### `ai-service/app/api/v1/chat.py`

Endpoints:

- `POST /api/v1/chat`: يستقبل `ChatRequest` ويرجع `ChatResponse` عبر `ChatService`.
- `GET /api/v1/chat/sessions`: يرجع `{ "status": "stateless" }`.

كل endpoint محمي بـ internal API key.

### `ai-service/app/api/v1/uploads.py`

Endpoints:

- `POST /api/v1/uploads/process`: يعالج upload عبر `UploadProcessor`.
- `POST /api/v1/meetings/upload`: deprecated ويرشد إلى `/api/v1/uploads/process`.
- `GET /api/v1/uploads/{upload_id}/status`: يرجع status stateless.

### `ai-service/app/api/v1/agents.py`

Placeholder:

- `POST /api/v1/agents/{agent_id}/runs`
- `GET /api/v1/agents/runs/{run_id}/steps`

الاستجابة الحالية `not_implemented`.

### `ai-service/app/api/v1/sources.py`

Placeholder:

- `GET /api/v1/chat/sources/{source_id}`

الاستجابة الحالية `not_implemented`.

### `ai-service/app/api/v1/workspace_graph.py`

Placeholder:

- `GET /api/v1/workspace/graph`

الاستجابة الحالية `not_implemented`.

## Core layer

### `ai-service/app/core/config.py`

يعرف `Settings` باستخدام `pydantic-settings`.

الإعدادات:

- `app_name`
- `database_url`
- `internal_api_key`
- `llm_provider`
- `groq_api_key`
- `groq_llm_model`
- `groq_transcription_model`
- `openai_api_key`
- `pinecone_api_key`
- `pinecone_index_name`

### `ai-service/app/core/security.py`

يتحقق من header:

```text
X-Internal-API-Key
```

إذا لم يطابق `settings.internal_api_key` يرجع HTTP 401.

### `ai-service/app/core/database.py`

يعرف SQLAlchemy base فقط:

- `Base(DeclarativeBase)`

لا يوجد engine/session/migrations فعلياً بعد.

### `ai-service/app/core/errors.py`

يعرف error code constants:

- `AI_VALIDATION_ERROR`
- `AI_PERMISSION_DENIED`
- `AI_NO_RELEVANT_DATA`
- `AI_EXTERNAL_SERVICE_FAILED`
- `AI_LOW_CONFIDENCE`
- `AI_PROCESSING_FAILED`

### `ai-service/app/core/logging.py`

Placeholder لإعداد logging.

## Schemas

### `ai-service/app/schemas/common.py`

يعرف:

- `UserContext`
- `AccessScope`

لكن endpoints الحالية لا تستخدم shared request shape الكامل الموجود في الخطة.

### `ai-service/app/schemas/chat.py`

يعرف:

- `ChatRequest`: يحتوي `project_id`, `question`, `context`.
- `ChatSource`: يحتوي `content`, `metadata`.
- `ChatResponse`: يحتوي `project_id`, `question`, `answer`, `sources`.

### `ai-service/app/schemas/upload.py`

يعرف:

- `ProcessUploadRequest`: يحتوي `upload_id`, `project_id`, واختيارياً `file_path`, `file_url`, `content`.
- `KnowledgeChunkResponse`: يحتوي `content`, `embedding`, `metadata`.
- `ProcessUploadResponse`: يحتوي `upload_id`, `project_id`, `transcript`, `summary`, `decisions`, `chunks`.

### Schemas placeholders

الملفات التالية موجودة كعناوين فقط:

- `meeting_intelligence.py`
- `agents.py`
- `knowledge.py`
- `sources.py`
- `errors.py`

## Services

### `ai-service/app/services/chat_service.py`

خدمة stateless للـ Q&A.

طريقة العمل:

- تأخذ أول 5 عناصر من `context`.
- تحول كل context إلى `ChatSource` مع metadata rank.
- إذا يوجد context، ترجع جواباً يبدأ بـ:

```text
Based on the project knowledge...
```

- إذا لا يوجد context، تخبر caller أنه لا توجد project knowledge في الطلب.

لا يوجد RAG حقيقي أو LLM call حالياً.

### `ai-service/app/services/upload_processor.py`

الخدمة الأساسية لمعالجة upload.

تعمل كالتالي:

1. حل مصدر الملف من `content` أو `file_path` أو `file_url`.
2. إذا كان صوتاً أو فيديو، يستدعي `MediaTranscriptionService`.
3. إذا كان نصاً/PDF/DOCX، يستخرج النص مباشرة.
4. يحلل transcript عبر `MeetingIntelligenceService`.
5. يقسم النص إلى chunks عبر `chunk_text`.
6. يولد embedding لكل chunk عبر `EmbeddingService`.
7. يحاول فهرسة chunks في Pinecone إذا كانت الإعدادات موجودة.
8. يستدعي hook للحفظ في DB، لكنه لا يخترع جداول غير معتمدة.
9. يرجع `ProcessUploadResponse`.

### `ai-service/app/services/meeting_intelligence_service.py`

منطق تحليل meeting intelligence:

- إذا كان `LLM_PROVIDER=groq` و`GROQ_API_KEY` موجوداً، يستخدم Groq LLM لإرجاع JSON فيه `summary`, `decisions`, `tasks`.
- إذا لم يكن Groq مفعلاً، يستخدم fallback rule-based:

- `summarize`: يأخذ أول 3 جمل.
- `extract_decisions`: يرجع أول 10 جمل تحتوي markers مثل `decided`, `decision`, `agreed`, `approved`, `will`.
- `_sentences`: يقسم النص إلى جمل باستخدام regex.

### `ai-service/app/services/media_transcription_service.py`

ينفذ مسار الصوت/الفيديو:

1. يتحقق من وجود `GROQ_API_KEY`.
2. يبحث عن `ffmpeg`.
3. يستخرج الصوت من الفيديو أو الصوت الأصلي.
4. يقسمه إلى MP3 chunks حسب `MEDIA_CHUNK_SECONDS`.
5. يرسل كل chunk إلى Groq Whisper عبر `GroqWhisperClient`.
6. يجمع transcript النهائي.

### `ai-service/app/services/embedding_service.py`

ينتج embedding حتمي محلي:

- يستخدم `hashlib.sha256`.
- يرجع list من floats بين `-1` و `1`.
- الافتراضي 16 dimensions.

هذا بديل local/dev وليس OpenAI embeddings.

### Services placeholders

الملفات التالية موجودة كـ placeholders:

- `rag_service.py`
- `knowledge_chunk_service.py`
- `pinecone_service.py`
- `agent_service.py`
- `source_service.py`
- `workspace_graph_service.py`

## Utils

### `ai-service/app/utils/chunking.py`

يعرف `chunk_text`.

السلوك:

- يطبع/ينظف المسافات إلى نص normalized.
- يقسم النص إلى chunks بحجم افتراضي `1200`.
- overlap افتراضي `150`.
- يرجع قائمة chunks.

### `ai-service/app/utils/file_extractors.py`

يعرف `extract_text_from_source`.

مصادر النص:

- `content`: يرجع كما هو.
- `file_path`: يقرأ ملف نصي محلي إذا موجود.
- `file_url`: يجلب URL عبر `urllib.request`.

إذا لا يوجد مصدر صالح يرجع HTTP 422.

ملاحظة: لا يوجد parsing حقيقي لـ PDF/DOCX/audio حالياً.

### Utils placeholders

الملفات التالية موجودة كـ placeholders:

- `citations.py`
- `confidence.py`
- `retry.py`

## Clients

ملفات clients:

- `groq_client.py`: يحتوي `GroqWhisperClient` و`GroqLlmClient`.
- `openai_client.py`
- `pinecone_client.py`
- `whisper_client.py`
- `mcp_client.py`

الـ calls الفعلية لـ Groq موجودة في `groq_client.py`. بقية clients ما زالت placeholders.

## Models

ملفات models موجودة كـ placeholders فقط:

- `ai_chat.py`
- `knowledge.py`
- `meetings.py`
- `agents.py`
- `feedback.py`

لا توجد SQLAlchemy models فعلية بعد.

## Tests

### `ai-service/app/tests/test_chat.py`

يغطي:

- نجاح chat عندما يصل context.
- chat بدون context يرجع رسالة تفيد أن الخدمة لا تملك project knowledge في الطلب.

### `ai-service/app/tests/test_uploads.py`

يغطي:

- `/api/v1/uploads/process` يرجع payload جاهز للـ Laravel/PHP فيه summary و decisions و chunks و embedding.
- endpoint يرفض الطلب بدون internal API key.

### Tests placeholders

الملفات التالية موجودة كعناوين فقط:

- `test_rag.py`
- `test_agents.py`
- `test_permissions.py`

## GitHub workflows

### `.github/workflows/auto-assign.yml`

Workflow للـ GitHub. لم يتم تحليل تفاصيله بعمق لأنه ليس جزءاً من خدمة FastAPI نفسها.

### `.github/workflows/proof-html.yml`

Workflow للـ GitHub. لم يتم تحليل تفاصيله بعمق لأنه ليس جزءاً من خدمة FastAPI نفسها.

## Postman files

### `ai-service/.postman/resources.yaml`

ملف resources تابع لـ Postman.

### `ai-service/postman/globals/workspace.globals.yaml`

ملف globals لـ Postman workspace.

## ملاحظات مهمة

- يوجد فرق واضح بين الوثائق الطموحة والتنفيذ الحالي.
- التنفيذ الحالي مناسب كبداية local/dev لإثبات flow، وليس production AI service مكتملة.
- لا يوجد persistence فعلي في PostgreSQL حتى الآن لأن migrations/tables غير موجودة.
- Groq transcription وGroq LLM مطبقان ويحتاجان `GROQ_API_KEY`.
- Pinecone indexing موجود كـ best-effort hook عند ضبط `PINECONE_API_KEY` و`PINECONE_INDEX_NAME`.
- لا يوجد RAG retrieval فعلي حتى الآن.
- لا يوجد permission scope enforcement فعلي سوى internal API key.
- لا يوجد seed/demo data runtime؛ تم حذف ملف `ai-service/app/seeds/demo_data.py`.
- بعض الوثائق تشير إلى JWT و Docker demo و endpoints غير موجودة في الكود الحالي.
- بعض النصوص العربية في `demo-script.md` ظاهرة بترميز غير صحيح وتحتاج تصحيح.

## أقرب خطوات مقترحة

1. توحيد الوثائق مع endpoints الحالية أو تعديل الكود ليطابق contract النهائي.
2. إضافة migrations/tables معتمدة لحفظ نتائج upload processing.
3. استبدال embeddings المحلية بمزود embeddings production.
4. ربط Pinecone search داخل RAG.
5. ربط Groq LLM للـ chat.
6. تنفيذ RAG service وربطه بـ `/chat`.
7. تطبيق access scope القادم من PHP Backend.
8. إكمال agents/sources/workspace graph أو إزالة endpoints غير الجاهزة من contract المؤقت.
9. توسيع الاختبارات لتغطي security، chunking، file extraction، RAG، upload failures.
