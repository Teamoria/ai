# Backend Upload -> AI Extraction Plan

##
```text
Frontend
  -> Backend يرفع ويحفظ الملف
  -> Backend يستدعي AI extraction endpoint
  -> AI يرجع transcript/summary/tasks/decisions/indexed_chunk_count
  -> Backend يحفظ النتيجة ويرجعها للـ Frontend
```

## Endpoint ثابت للاستخراج

استخدم هذا endpoint كالعقد الثابت بين الـ Backend وخدمة الـ AI:

```http
POST /api/v1/extractions/process
Content-Type: application/json
X-Internal-API-Key: <INTERNAL_API_KEY>
```

Base URL محلي:

```text
http://127.0.0.1:8001
```

الرابط الكامل:

```text
http://127.0.0.1:8001/api/v1/extractions/process
```

## Request Body

الـ Backend يرسل واحد فقط من هذه الحقول:

```text
file_path
file_url
content
```

## Adopted integration mode

Laravel owns uploads, storage, authorization, processing status, and database
persistence. The AI service only receives a file reference, processes it, and
returns JSON.

Preferred request from Laravel:

```json
{
  "upload_id": "upload-id-from-laravel",
  "project_id": "project-id-from-laravel",
  "file_url": "https://backend.example.com/api/v1/internal/uploads/upload-id/file"
}
```

If Laravel's file URL needs internal headers, configure the AI service:

```text
BACKEND_FILE_API_KEY=<laravel internal or x-api-key value>
BACKEND_FILE_API_KEY_HEADER=x-api-key
BACKEND_FILE_BEARER_TOKEN=
```

Alternatively, Laravel can send per-request headers:

```json
{
  "upload_id": "upload-id-from-laravel",
  "project_id": "project-id-from-laravel",
  "file_url": "https://backend.example.com/api/v1/internal/uploads/upload-id/file",
  "file_url_headers": {
    "x-api-key": "internal-key"
  }
}
```

The AI response keeps `persisted=false`; Laravel stores the returned transcript,
summary, decisions, tasks, and processing status in its own tables.

### الخيار الأفضل إذا نفس السيرفر أو نفس Docker network

```json
{
  "upload_id": "upload-id-from-backend",
  "project_id": "project-id-from-backend",
  "file_path": "C:\\storage\\uploads\\meeting.mp4"
}
```

شرط مهم: `file_path` لازم يكون قابل للقراءة من الجهاز أو الحاوية التي تشغل AI Service.

### الخيار الأفضل إذا التخزين عند backend أو object storage

```json
{
  "upload_id": "upload-id-from-backend",
  "project_id": "project-id-from-backend",
  "file_url": "https://backend.local/internal/files/meeting.mp4"
}
```

شرط مهم: الرابط يجب أن يكون داخلي وآمن وقابل للتحميل من AI Service.

### خيار النص المباشر للاختبار

```json
{
  "upload_id": "upload-id-from-backend",
  "project_id": "project-id-from-backend",
  "content": "Meeting transcript text here."
}
```

## Response Body

خدمة الـ AI ترجع للـ Backend:

```json
{
  "upload_id": "upload-id-from-backend",
  "project_id": "project-id-from-backend",
  "source_type": "text",
  "transcript": "Full extracted text or transcription.",
  "transcript_quality": {
    "level": "good",
    "score": 80,
    "word_count": 120,
    "unique_word_ratio": 0.7,
    "warning": null,
    "suggestions": []
  },
  "summary": "Human readable summary.",
  "structured_summary": {
    "title": null,
    "overview": "Short overview.",
    "priority": null,
    "key_points": [],
    "task_count": 1,
    "decision_count": 1
  },
  "decisions": [
    "Decision text"
  ],
  "decision_items": [
    {
      "title": "Decision title",
      "description": "Decision description",
      "confidence": "medium"
    }
  ],
  "tasks": [
    "Task text"
  ],
  "task_items": [
    {
      "title": "Task title",
      "description": "Task description",
      "category": null,
      "priority": null,
      "assignee": null,
      "status": "pending"
    }
  ],
  "indexed_chunk_count": 8,
  "persisted": false
}
```

مهم: خدمة الـ AI لا ترجع `chunks` ولا `embedding` للـ Backend في هذا الـ response.  
الـ chunks يتم توليدها داخليا وفهرستها في Pinecone/vector database، والـ Backend يحفظ فقط `indexed_chunk_count`.

## Backend Responsibilities

1. يستقبل الملف من الـ Frontend.
2. يتحقق من المستخدم والصلاحيات.
3. يحفظ الملف عنده.
4. ينشئ upload record في قاعدة بياناته.
5. يستدعي:

```http
POST /api/v1/extractions/process
```

6. يرسل `upload_id`, `project_id`, و `file_path` أو `file_url`.
7. يستقبل نتيجة AI.
8. يحفظ في قاعدة بياناته:

```text
transcript
summary
structured_summary
decisions
decision_items
tasks
task_items
indexed_chunk_count
processing_status = processed أو failed
```

9. يرجع النتيجة للـ Frontend.

## AI Service Responsibilities

1. تستقبل request من Backend فقط.
2. تتحقق من `X-Internal-API-Key`.
3. تقرأ الملف من `file_path` أو `file_url`.
4. تستخرج النص من PDF/DOCX/TXT أو تحول audio/video إلى transcript.
5. تولد summary, decisions, tasks, chunks داخليا.
6. ترجع JSON للـ Backend.
7. تفهرس الـ chunks في Pinecone إذا كانت الإعدادات مفعلة.
8. لا تعتمد على تخزين الملف عندها في هذا السيناريو.

## Supported Inputs

Text:

```text
.txt, .md, .csv, .json, .srt, .vtt, .log
```

Documents:

```text
.pdf, .docx, .xlsx
```

Images:

```text
.png, .jpg, .jpeg, .gif, .bmp, .tiff, .webp
```

Audio/video:

```text
.mp3, .mp4, .mpeg, .mpga, .m4a, .wav, .webm, .mov, .avi, .mkv
```

## Laravel Example

```php
$response = Http::withHeaders([
    'X-Internal-API-Key' => config('services.ai.internal_api_key'),
])->post(config('services.ai.base_url') . '/api/v1/extractions/process', [
    'upload_id' => (string) $upload->id,
    'project_id' => (string) $upload->project_id,
    'file_path' => $upload->stored_path,
]);

if ($response->successful()) {
    $ai = $response->json();

    $upload->update([
        'processing_status' => 'processed',
        'transcript' => $ai['transcript'],
        'summary' => $ai['summary'],
        'ai_payload' => $ai,
    ]);
} else {
    $upload->update([
        'processing_status' => 'failed',
        'processing_error' => $response->body(),
    ]);
}
```

## PowerShell Test

```powershell
$body = @{
  upload_id = "upload-1"
  project_id = "project-1"
  content = "The team decided to use one stable extraction endpoint."
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8001/api/v1/extractions/process" `
  -Headers @{"X-Internal-API-Key"="change_me"} `
  -ContentType "application/json" `
  -Body $body
```

## قرار نهائي

اعتمدوا endpoint واحد ثابت للاستخراج:

```http
POST /api/v1/extractions/process
```

ولا تجعلوا الـ Frontend يستدعي AI Service مباشرة.  
الـ Frontend يرفع للـ Backend فقط، والـ Backend يستدعي AI Service داخليا.

## Vector Search داخل Pinecone

بعد ما يتم استخراج الملف وفهرسة الـ chunks في Pinecone، يستخدم الـ Backend endpoint ثابت للبحث:

```http
POST /api/v1/retrieval/query
Content-Type: application/json
X-Internal-API-Key: <INTERNAL_API_KEY>
```

Request:

```json
{
  "project_id": "project-1",
  "question": "ما هي المهام المطلوبة؟",
  "top_k": 5
}
```

ماذا يحدث داخل AI Service:

```text
1. يحول السؤال إلى embedding.
2. يحدد namespace الخاص بالمشروع:
   teamoria-{project_id}
3. يبحث في Pinecone عن أقرب chunks.
4. يرسل الـ chunks للـ LLM.
5. يرجع answer + sources.
```

Response:

```json
{
  "project_id": "project-1",
  "question": "ما هي المهام المطلوبة؟",
  "answer": "المهام المطلوبة هي ...",
  "sources": [
    {
      "content": "النص الذي تم الاعتماد عليه...",
      "score": 0.91,
      "metadata": {
        "upload_id": "upload-1",
        "project_id": "project-1",
        "chunk_index": 0,
        "source_type": "pdf"
      }
    }
  ]
}
```

إعدادات `.env` المطلوبة للـ Pinecone:

```text
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=...
PINECONE_NAMESPACE_PREFIX=teamoria
EMBEDDING_DIMENSIONS=1024
```

إذا استخدمت namespace ثابت بدل namespace لكل مشروع:

```text
PINECONE_NAMESPACE=your-fixed-namespace
```
