# Teamoria AI Service Backend API Contract

This document lists the AI Service APIs that are ready for the PHP Backend to call.

هذه الوثيقة توضّح الـ APIs الجاهزة في خدمة الذكاء الاصطناعي والتي يمكن للـ PHP Backend استخدامها.

## Architecture / المعمارية

```text
Frontend
  -> PHP Backend
  -> FastAPI AI Service
  -> Groq / ffmpeg / Pinecone hooks
```

The frontend must not call the AI Service directly. The PHP Backend is responsible for authentication, authorization, file storage, database persistence, and returning the final response to the frontend.

الـ frontend لا يستدعي خدمة الـ AI مباشرة. الـ PHP Backend هو المسؤول عن تسجيل الدخول والصلاحيات وتخزين الملفات والحفظ في قاعدة البيانات وإرجاع النتيجة للواجهة.

## Base URL / الرابط الأساسي

Local development:

```text
http://127.0.0.1:8001
```

API prefix:

```text
/api/v1
```

## Authentication / التوثيق الداخلي

All protected endpoints require this header:

كل endpoints المحمية تحتاج هذا الهيدر:

```http
X-Internal-API-Key: change_me
```

The value must match `INTERNAL_API_KEY` in `ai-service/.env`.

القيمة يجب أن تطابق `INTERNAL_API_KEY` في ملف `ai-service/.env`.

## Environment Requirements / متطلبات التشغيل

For text/PDF/DOCX processing:

```text
INTERNAL_API_KEY
```

For audio/video processing:

```text
GROQ_API_KEY
FFMPEG_PATH=ffmpeg
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3-turbo
GROQ_LLM_MODEL=llama-3.3-70b-versatile
```

Optional Pinecone indexing:

```text
PINECONE_API_KEY
PINECONE_INDEX_NAME
PINECONE_NAMESPACE_PREFIX=teamoria
```

## Ready Endpoints / الـ APIs الجاهزة

## 1. Health Check / فحص تشغيل الخدمة

### Request

```http
GET /health
```

### Response

```json
{
  "status": "ok"
}
```

### Backend usage / استخدام الباكند

Use this endpoint to verify that the AI Service is running before integration tests or deployment checks.

استخدم هذا endpoint للتأكد أن خدمة الـ AI تعمل قبل اختبارات الربط أو النشر.

## 2. Process Upload / معالجة ملف أو نص

### Request

```http
POST /api/v1/uploads/process
X-Internal-API-Key: change_me
Content-Type: application/json
```

### Purpose / الهدف

This endpoint processes uploaded content or a stored file. It can:

- Read direct text content.
- Read local text files.
- Read PDF files.
- Read DOCX files.
- Process audio/video files through `ffmpeg` and Groq Whisper.
- Generate summary, decisions, and tasks.
- Split transcript into chunks.
- Generate local embeddings.
- Optionally index chunks in Pinecone if configured.

هذا endpoint يعالج النص أو الملف المخزن. يستطيع:

- قراءة نص مباشر.
- قراءة ملفات نصية.
- قراءة PDF.
- قراءة DOCX.
- معالجة الصوت والفيديو عبر `ffmpeg` و Groq Whisper.
- توليد ملخص وقرارات ومهام.
- تقسيم النص إلى chunks.
- توليد embeddings محلية.
- فهرسة chunks في Pinecone إذا كانت الإعدادات مفعّلة.

### Request Body Options / أشكال الطلب

Send exactly one source field: `content`, `file_path`, or `file_url`.

أرسل واحد فقط من مصادر الملف: `content` أو `file_path` أو `file_url`.

### Option A: Direct Text / نص مباشر

```json
{
  "upload_id": "upload-1",
  "project_id": "project-1",
  "content": "Today we reviewed the backend integration. The team decided to connect Laravel uploads to FastAPI. Ahmad will prepare the frontend demo tomorrow."
}
```

### Option B: Local File Path / مسار ملف محلي

```json
{
  "upload_id": "upload-2",
  "project_id": "project-1",
  "file_path": "C:\\storage\\uploads\\meeting.mp4"
}
```

Important: `file_path` must be readable from the machine/container running the AI Service.

مهم: `file_path` يجب أن يكون قابلاً للقراءة من نفس الجهاز/الحاوية التي تشغل خدمة الـ AI.

### Option C: Internal File URL / رابط ملف داخلي

```json
{
  "upload_id": "upload-3",
  "project_id": "project-1",
  "file_url": "https://internal-storage.example.com/files/meeting.mp4"
}
```

Use `file_url` when PHP stores files in object storage or a private internal file service.

استخدم `file_url` عندما يحفظ PHP الملفات في object storage أو خدمة ملفات داخلية.

### Supported Input Types / الأنواع المدعومة

Text-like files:

```text
.txt, .md, .csv, .json, .srt, .vtt, .log
```

Documents:

```text
.pdf, .docx
```

Audio/video:

```text
.mp3, .mp4, .mpeg, .mpga, .m4a, .wav, .webm, .mov, .avi, .mkv
```

### Success Response / استجابة النجاح

```json
{
  "upload_id": "upload-1",
  "project_id": "project-1",
  "source_type": "text",
  "document_type": "meeting",
  "transcript": "Today we reviewed the backend integration. The team decided to connect Laravel uploads to FastAPI. Ahmad will prepare the frontend demo tomorrow.",
  "summary": "Main discussion: Today we reviewed the backend integration. Key decision: The team decided to connect Laravel uploads to FastAPI. Next action: Ahmad will prepare the frontend demo tomorrow.",
  "structured_result": {
    "overview": "...",
    "decisions": [],
    "tasks": []
  },
  "decisions": [
    "The team decided to connect Laravel uploads to FastAPI."
  ],
  "tasks": [
    "Ahmad will prepare the frontend demo tomorrow."
  ],
  "quality": {
    "extraction": "high",
    "analysis": "high",
    "requires_review": false
  },
  "warnings": [],
  "chunks": [
    {
      "content": "Today we reviewed the backend integration...",
      "embedding": [0.12, -0.44],
      "metadata": {
        "chunk_index": 0,
        "source": "content",
        "source_type": "text"
      }
    }
  ],
  "indexed_chunk_count": 0,
  "persisted": false
}
```

### Response Fields / شرح الحقول

| Field | English | عربي |
|---|---|---|
| `upload_id` | Upload ID sent by PHP | رقم الملف المرسل من PHP |
| `project_id` | Project ID sent by PHP | رقم المشروع المرسل من PHP |
| `source_type` | Detected source type: `text`, `pdf`, `docx`, or `media` | نوع المصدر المكتشف |
| `document_type` | Detected content type: `cv`, `meeting`, `document`, `media`, or `spreadsheet` | نوع المحتوى المكتشف |
| `transcript` | Extracted text or audio/video transcript | النص المستخرج أو المحول من الصوت/الفيديو |
| `summary` | Human-readable summary | ملخص مفهوم |
| `structured_result` | Type-specific result for frontend rendering. CVs include candidate, contact, skills, projects, strengths, gaps, and score. Meetings include decisions and tasks. Documents include title, overview, key points, and topics. | نتيجة منظمة حسب نوع الملف للعرض في الواجهة |
| `decisions` | Extracted decisions | القرارات المستخرجة |
| `tasks` | Extracted action items/tasks | المهام المستخرجة |
| `quality` | Extraction and analysis quality flags | مؤشرات جودة الاستخراج والتحليل |
| `warnings` | User-facing processing warnings when text is short, medium quality, or may require review | تحذيرات المعالجة عند الحاجة للمراجعة |
| `chunks` | Text chunks prepared for RAG/indexing | أجزاء النص الجاهزة للبحث والفهرسة |
| `indexed_chunk_count` | Number of chunks indexed in Pinecone | عدد الـ chunks التي تم فهرستها في Pinecone |
| `persisted` | Whether AI Service saved to DB | هل خدمة الـ AI حفظت في DB |

### Important Persistence Note / ملاحظة مهمة عن الحفظ

Currently, `persisted` is expected to be `false`.

حالياً من المتوقع أن تكون `persisted=false`.

Reason: PHP Backend owns the main database tables and should save the AI result after receiving the response. The AI Service does not create new unapproved tables.

السبب: الـ PHP Backend هو مالك الجداول الأساسية ويجب أن يحفظ نتيجة الـ AI بعد استلامها. خدمة الـ AI لا تنشئ جداول جديدة غير معتمدة.

### PHP Backend Responsibilities / مسؤوليات PHP Backend

After receiving the AI response, PHP should save:

- `transcript`
- `summary`
- `decisions`
- `tasks`
- Processing status: `processed` or `failed`
- Any relation to `upload_id`, `project_id`, meeting, or user scope

بعد استلام النتيجة، يجب على PHP حفظ:

- النص الكامل `transcript`
- الملخص `summary`
- القرارات `decisions`
- المهام `tasks`
- حالة المعالجة
- الربط مع الملف والمشروع والاجتماع والصلاحيات

### Example PHP Flow / مسار PHP المقترح

```text
1. Frontend uploads file to PHP.
2. PHP validates user permissions.
3. PHP stores file.
4. PHP creates upload record.
5. PHP calls AI Service /api/v1/uploads/process.
6. PHP saves transcript, summary, decisions, and tasks.
7. PHP returns final result to frontend.
```

```text
1. الواجهة ترفع الملف إلى PHP.
2. PHP يتحقق من صلاحيات المستخدم.
3. PHP يخزن الملف.
4. PHP ينشئ record للملف.
5. PHP يستدعي AI Service.
6. PHP يحفظ النص والملخص والقرارات والمهام.
7. PHP يرجع النتيجة للواجهة.
```

## 3. Chat / المحادثة

### Request

```http
POST /api/v1/chat
X-Internal-API-Key: change_me
Content-Type: application/json
```

### Current Status / الحالة الحالية

This endpoint is currently a stateless project Q&A helper. It does not yet perform real RAG retrieval from Pinecone or the database.

هذا endpoint حالياً مساعد أسئلة بسيط بدون RAG حقيقي من Pinecone أو قاعدة البيانات.

### Request Body

```json
{
  "project_id": "project-1",
  "question": "What did the team decide?",
  "context": [
    "The team decided to connect Laravel uploads to FastAPI."
  ]
}
```

### Response

```json
{
  "project_id": "project-1",
  "question": "What did the team decide?",
  "answer": "Based on the project knowledge, the answer to 'What did the team decide?' is most likely found in: The team decided to connect Laravel uploads to FastAPI.",
  "sources": [
    {
      "content": "The team decided to connect Laravel uploads to FastAPI.",
      "metadata": {
        "rank": 1
      }
    }
  ]
}
```

### Backend usage / استخدام الباكند

Use this endpoint only for temporary testing with context sent directly by PHP. For production chat, the next step is to implement real RAG retrieval using stored chunks and Pinecone.

استخدم هذا endpoint مؤقتاً فقط عندما يرسل PHP الـ context مباشرة. للـ production يجب تنفيذ RAG حقيقي باستخدام chunks المخزنة وPinecone.

## 4. Chat Sessions / جلسات المحادثة

### Request

```http
GET /api/v1/chat/sessions
X-Internal-API-Key: change_me
```

### Response

```json
{
  "status": "stateless"
}
```

### Status / الحالة

Placeholder only. No persistent chat sessions are implemented yet.

هذا placeholder فقط. لا توجد جلسات محادثة محفوظة حالياً.

## 5. Upload Status / حالة المعالجة

### Request

```http
GET /api/v1/uploads/{upload_id}/status
X-Internal-API-Key: change_me
```

### Response

```json
{
  "upload_id": "upload-1",
  "status": "stateless"
}
```

### Status / الحالة

Placeholder only. PHP should currently own upload processing status in its database.

هذا placeholder فقط. حالياً PHP يجب أن يحفظ حالة المعالجة في قاعدة البيانات عنده.

## 6. Deprecated Meeting Upload / endpoint قديم

### Request

```http
POST /api/v1/meetings/upload
X-Internal-API-Key: change_me
```

### Response

```json
{
  "status": "deprecated",
  "replacement": "/api/v1/uploads/process"
}
```

### Backend usage / استخدام الباكند

Do not use this endpoint. Use `/api/v1/uploads/process`.

لا تستخدم هذا endpoint. استخدم `/api/v1/uploads/process`.

## 7. Not Ready Yet / غير جاهز بعد

These endpoints exist but return `not_implemented`:

هذه endpoints موجودة لكنها غير منفذة بعد:

```http
POST /api/v1/agents/{agent_id}/runs
GET /api/v1/agents/runs/{run_id}/steps
GET /api/v1/chat/sources/{source_id}
GET /api/v1/workspace/graph
```

Do not build production PHP flows on these endpoints yet.

لا تبني ربط production عليها حالياً.

## Backend Checklist / قائمة تنفيذ للباكند

- Create/confirm upload endpoint in PHP for frontend file uploads.
- Store the uploaded file.
- Create an upload record and get `upload_id`.
- Call `POST /api/v1/uploads/process`.
- Send `file_path` or `file_url`, not the raw multipart file.
- Save `transcript`, `summary`, `decisions`, and `tasks`.
- Return saved results to frontend.
- Store processing errors if AI Service returns non-2xx.
- Do not expose `X-Internal-API-Key` to frontend.

---

- إنشاء/تأكيد endpoint في PHP لرفع الملفات من الواجهة.
- تخزين الملف.
- إنشاء record للملف واستخراج `upload_id`.
- استدعاء `POST /api/v1/uploads/process`.
- إرسال `file_path` أو `file_url` وليس multipart file مباشرة.
- حفظ `transcript`, `summary`, `decisions`, `tasks`.
- إرجاع النتائج للواجهة.
- حفظ أخطاء المعالجة إذا رجعت خدمة الـ AI خطأ.
- عدم كشف `X-Internal-API-Key` للواجهة.

## Quick Test / اختبار سريع

PowerShell:

```powershell
$body = @{
  upload_id = "upload-1"
  project_id = "project-1"
  content = "Today we reviewed the backend integration. The team decided to connect Laravel uploads to FastAPI. Ahmad will prepare the frontend demo tomorrow."
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8001/api/v1/uploads/process" `
  -Headers @{"X-Internal-API-Key"="change_me"} `
  -ContentType "application/json" `
  -Body $body
```

Expected important fields:

```text
source_type: text
summary: Main discussion / Key decision / Next action
decisions: one or more decisions
tasks: one or more tasks
persisted: false
```
