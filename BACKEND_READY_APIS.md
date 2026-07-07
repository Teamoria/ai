# Teamoria AI Service - Ready Backend APIs

هذا الملف هو نسخة تسليم مختصرة للـ Backend team بعد قراءة ملفات المشروع والـ FastAPI routes.

## تحديث مهم

الـ AI Service لم يعد يملك Upload management APIs ولا جداول تخزين upload داخل قاعدة بياناته.
Laravel هو المسؤول عن:

```text
POST /api/v1/uploads
GET /api/v1/uploads
GET /api/v1/uploads/{upload}
GET /api/v1/uploads/{upload}/status
GET /api/v1/uploads/{upload}/download
DELETE /api/v1/uploads/{upload}
POST/DELETE upload permissions
```

الـ AI Service يستخدم فقط لمعالجة ملف أو نص وإرجاع JSON:

```http
POST /api/v1/extractions/process
```

ويبقى alias القديم متاحاً للتوافق:

```http
POST /api/v1/uploads/process
```

## ملاحظة تشغيل مهمة

هذا المشروع ليس Laravel/PHP داخل هذا المجلد، لذلك الأمر التالي لن يعمل هنا:

```powershell
C:\php85\php.exe -S 127.0.0.1:8000 -t public public/index.php
```

السبب: لا يوجد مجلد `public`.

تشغيل خدمة الـ AI يكون من داخل `ai-service`:

```powershell
cd ai-service
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Base URL المحلي:

```text
http://127.0.0.1:8001
```

API prefix:

```text
/api/v1
```

## Authentication

كل endpoints المحمية تحتاج:

```http
X-Internal-API-Key: <INTERNAL_API_KEY>
```

القيمة يجب أن تطابق:

```text
ai-service/.env -> INTERNAL_API_KEY
```

Endpoints إدارة الملفات تحتاج أيضا معلومات المستخدم:

```http
X-User-Id: <user_id>
X-User-Role: <member|company_owner|admin>
X-Company-Id: <company_id optional>
```

لا ترسل `X-Internal-API-Key` من الـ frontend. فقط PHP/Laravel backend يستدعي هذه الخدمة.

## APIs جاهزة للربط

### 1. Health Check

```http
GET /health
```

لا يحتاج API key.

Response:

```json
{
  "status": "ok"
}
```

### 2. Upload Files

```http
POST /api/v1/uploads
Content-Type: multipart/form-data
X-Internal-API-Key: <INTERNAL_API_KEY>
X-User-Id: <user_id>
X-User-Role: <role>
X-Company-Id: <company_id optional>
```

Form fields:

```text
files: one or more files
scope: personal | company | project | task
visibility: private | members | selected
company_id: required if scope=company, optional otherwise
project_id: required if scope=project
task_id: required if scope=task
access_level: view | manage
shared_with_user_ids: required when visibility=selected
```

ماذا يفعل:

- يحفظ الملف في تخزين خدمة الـ AI.
- ينشئ upload record.
- يبدأ معالجة AI بالخلفية.
- يرجع حالة أولية مثل `queued`.
- إذا الملف موجود ومحلل سابقا يرجع نفس التحليل بدل التكرار.

Response shape:

```json
{
  "success": true,
  "message": "Files uploaded successfully",
  "data": {
    "uploads": [
      {
        "id": "upload-id",
        "user_id": "user-id",
        "company_id": "company-id",
        "project_id": "project-id",
        "task_id": null,
        "original_name": "meeting.txt",
        "mime_type": "text/plain",
        "content_hash": "sha256",
        "extension": "txt",
        "size": 123,
        "scope": "project",
        "visibility": "private",
        "processing_status": "queued",
        "processing_stage": "queued",
        "processing_progress": 10,
        "processing_message": "File uploaded. Waiting to start AI processing.",
        "processing_error": null,
        "processed_at": null,
        "created_at": "..."
      }
    ]
  }
}
```

### 3. List Uploads

```http
GET /api/v1/uploads
X-Internal-API-Key: <INTERNAL_API_KEY>
X-User-Id: <user_id>
X-User-Role: <role>
X-Company-Id: <company_id optional>
```

Query params:

```text
scope: optional
visibility: optional
project_id: optional
task_id: optional
per_page: 1..100, default 50
```

Aliases جاهزة:

```http
GET /api/v1/uploads/list
GET /api/v1/uploads/mine
GET /api/v1/uploads/{project_id}/list
```

### 4. Get Upload Details

```http
GET /api/v1/uploads/{upload_id}
X-Internal-API-Key: <INTERNAL_API_KEY>
X-User-Id: <user_id>
X-User-Role: <role>
X-Company-Id: <company_id optional>
```

يرجع بيانات الملف مع نتائج التحليل إن وجدت:

```json
{
  "success": true,
  "message": "Upload retrieved successfully",
  "data": {
    "upload": {
      "id": "upload-id",
      "processing_status": "processed",
      "summary": {
        "transcript": "...",
        "summary": "...",
        "structured_summary": {
          "title": null,
          "overview": "...",
          "priority": null,
          "key_points": [],
          "task_count": 1,
          "decision_count": 1
        },
        "source_type": "document"
      },
      "decisions": [],
      "tasks": [],
      "chunks_count": 1,
      "chunks": []
    }
  }
}
```

### 5. Upload Processing Status

```http
GET /api/v1/uploads/{upload_id}/status
X-Internal-API-Key: <INTERNAL_API_KEY>
X-User-Id: <user_id>
X-User-Role: <role>
X-Company-Id: <company_id optional>
```

Response:

```json
{
  "upload_id": "upload-id",
  "status": "processing",
  "stage": "analyzing",
  "progress": 55,
  "message": "Analyzing the content and preparing the summary.",
  "processing_error": null
}
```

Stages الممكنة:

```text
queued, processing, extracting, transcribing, analyzing, chunking, indexing, saving, processed, failed, skipped
```

### 6. Download Upload

```http
GET /api/v1/uploads/{upload_id}/download
X-Internal-API-Key: <INTERNAL_API_KEY>
X-User-Id: <user_id>
X-User-Role: <role>
X-Company-Id: <company_id optional>
```

يرجع الملف الأصلي كـ binary response.

### 7. Delete Upload

```http
DELETE /api/v1/uploads/{upload_id}
X-Internal-API-Key: <INTERNAL_API_KEY>
X-User-Id: <user_id>
X-User-Role: <role>
X-Company-Id: <company_id optional>
```

Soft delete وليس حذف فعلي من قاعدة البيانات.

### 8. Add Upload Permission

```http
POST /api/v1/uploads/{upload_id}/permissions
Content-Type: application/x-www-form-urlencoded
X-Internal-API-Key: <INTERNAL_API_KEY>
X-User-Id: <user_id>
X-User-Role: <role>
X-Company-Id: <company_id optional>
```

Form fields:

```text
user_id: required
access_level: view | manage
```

### 9. Remove Upload Permission

```http
DELETE /api/v1/uploads/{upload_id}/permissions/{user_id}
X-Internal-API-Key: <INTERNAL_API_KEY>
X-User-Id: <user_id>
X-User-Role: <role>
X-Company-Id: <company_id optional>
```

### 10. Process Upload Directly

```http
POST /api/v1/uploads/process
Content-Type: application/json
X-Internal-API-Key: <INTERNAL_API_KEY>
```

Body: أرسل واحد فقط من `content`, `file_path`, `file_url`.

نص مباشر:

```json
{
  "upload_id": "upload-1",
  "project_id": "project-1",
  "content": "Meeting text or transcript goes here."
}
```

ملف محفوظ:

```json
{
  "upload_id": "upload-1",
  "project_id": "project-1",
  "file_path": "C:\\storage\\uploads\\meeting.mp4"
}
```

Response:

```json
{
  "upload_id": "upload-1",
  "project_id": "project-1",
  "source_type": "text",
  "transcript": "...",
  "transcript_quality": {
    "level": "good",
    "score": 80,
    "word_count": 100,
    "unique_word_ratio": 0.7,
    "warning": null,
    "suggestions": []
  },
  "summary": "...",
  "structured_summary": {
    "title": null,
    "overview": "...",
    "priority": null,
    "key_points": [],
    "task_count": 1,
    "decision_count": 1
  },
  "decisions": [],
  "decision_items": [],
  "tasks": [],
  "task_items": [],
  "indexed_chunk_count": 8,
  "persisted": false
}
```

`chunks` و `embedding` لا يتم إرجاعها للـ Backend في هذا response. يتم توليدها داخليا وفهرستها في Pinecone/vector database، والـ Backend يحفظ `indexed_chunk_count` فقط.

مهم: هذا endpoint يعالج ويرجع النتيجة مباشرة، لكنه لا يحفظ في DB الرئيسي. قيمة `persisted` تكون غالبا `false`.

### 11. Chat

```http
POST /api/v1/chat
Content-Type: application/json
X-Internal-API-Key: <INTERNAL_API_KEY>
```

Body:

```json
{
  "project_id": "project-1",
  "question": "What did the team decide?",
  "context": [
    "The team decided to connect Laravel uploads to FastAPI."
  ],
  "user": {
    "id": "user-id",
    "company_id": "company-id",
    "role": "member"
  }
}
```

`message` يمكن استخدامه بدل `question`.

Response:

```json
{
  "project_id": "project-1",
  "question": "What did the team decide?",
  "answer": "...",
  "sources": [
    {
      "content": "...",
      "metadata": {
        "rank": 1
      }
    }
  ]
}
```

ملاحظة: المحادثة حاليا stateless وتعتمد على `context` المرسل من الـ backend، وليست RAG كامل من قاعدة البيانات.

### 12. AI Conversations Alias

يوجد endpointان يعملان بنفس منطق Chat:

```http
POST /api/v1/ai/conversations
POST /ai/conversations
```

نفس body والـ response الخاص بـ `/api/v1/chat`.

### 13. Chat Sessions Status

```http
GET /api/v1/chat/sessions
X-Internal-API-Key: <INTERNAL_API_KEY>
```

Response:

```json
{
  "status": "stateless"
}
```

هذا endpoint موجود لكنه ليس جلسات محفوظة بعد.

### 14. Deprecated Meeting Upload

```http
POST /api/v1/meetings/upload
X-Internal-API-Key: <INTERNAL_API_KEY>
```

Response:

```json
{
  "status": "deprecated",
  "replacement": "/api/v1/uploads/process"
}
```

لا تستخدمه في production. استخدم `/api/v1/uploads` أو `/api/v1/uploads/process`.

## Endpoints موجودة لكنها غير جاهزة

هذه موجودة في الكود لكنها ترجع `not_implemented`:

```http
POST /api/v1/agents/{agent_id}/runs
GET /api/v1/agents/runs/{run_id}/steps
GET /api/v1/chat/sources/{source_id}
GET /api/v1/workspace/graph
```

لا يعتمد عليها Backend team حاليا.

## Laravel Integration Example

```php
$response = Http::withHeaders([
    'X-Internal-API-Key' => config('services.ai.internal_api_key'),
    'X-User-Id' => (string) auth()->id(),
    'X-User-Role' => auth()->user()->role ?? 'member',
    'X-Company-Id' => (string) auth()->user()->company_id,
])->attach(
    'files',
    fopen($path, 'r'),
    basename($path)
)->post(config('services.ai.base_url') . '/api/v1/uploads', [
    'scope' => 'project',
    'visibility' => 'private',
    'project_id' => (string) $project->id,
]);
```

إعدادات Laravel المقترحة:

```text
AI_SERVICE_BASE_URL=http://127.0.0.1:8001
AI_SERVICE_INTERNAL_API_KEY=<same as ai-service INTERNAL_API_KEY>
```

## الملفات التي تم الاعتماد عليها

```text
ai-service/app/main.py
ai-service/app/api/v1/router.py
ai-service/app/api/v1/uploads.py
ai-service/app/api/v1/chat.py
ai-service/app/api/v1/agents.py
ai-service/app/api/v1/sources.py
ai-service/app/api/v1/workspace_graph.py
ai-service/app/schemas/upload.py
ai-service/app/schemas/chat.py
ai-service/app/services/upload_management_service.py
ai-service/app/tests/test_uploads.py
ai-service/app/tests/test_chat.py
```
