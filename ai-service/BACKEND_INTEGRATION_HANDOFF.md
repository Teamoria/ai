# Teamoria AI Service - Backend Handoff

Use this when sharing the AI service API with the PHP/Laravel backend team.

## Base URL

Local:

```text
http://127.0.0.1:8001/api/v1
```

## Required Header

The current service uses this internal header:

```http
X-Internal-API-Key: <INTERNAL_API_KEY>
```

The value must match:

```text
ai-service/.env -> INTERNAL_API_KEY
```

Do not send this key from the frontend. Only the backend should call the AI service.

## Postman Files

Import these two files into Postman:

```text
ai-service/postman/Teamoria AI Service.postman_collection.json
ai-service/postman/Teamoria AI Service.postman_environment.json
```

After import, open the environment and set:

```text
internal_api_key = same value as INTERNAL_API_KEY in ai-service/.env
base_url = http://127.0.0.1:8001
```

## Main Upload API

Laravel owns upload APIs, storage, permissions, processing status, and database
tables. The AI service does not expose upload storage/list/detail/download/delete
endpoints and does not create upload-related database tables.

Process a Laravel-owned ready file directly:

```http
POST /api/v1/extractions/process-file
Content-Type: multipart/form-data
X-Internal-API-Key: <INTERNAL_API_KEY>
```

Required form fields:

```text
upload_id
file
```

Optional form fields:

```text
company_id
project_id
task_id
scope
visibility
job_description
transcription_language
```

Laravel should use this endpoint when it already has the uploaded file and wants
to send the binary file directly to the AI service without exposing a file URL.

Example fields:

```text
upload_id=123
scope=project
visibility=members
transcription_language=ar
file=@contract.pdf
```

The AI service stores the uploaded binary in a temporary file only for the
duration of processing, then deletes it. Laravel remains responsible for
permanent storage, permissions, processing status, and database persistence.

Legacy JSON processing is still available for raw text, local paths, or a
Laravel-owned internal URL:

```http
POST /api/v1/extractions/process
Content-Type: application/json
X-Internal-API-Key: <INTERNAL_API_KEY>
```

Example body:

```json
{
  "upload_id": "upload-1",
  "project_id": "project-1",
  "content": "Meeting text or transcript goes here."
}
```

Or with a stored file path that the AI service can read:

```json
{
  "upload_id": "upload-1",
  "project_id": "project-1",
  "file_path": "C:\\storage\\uploads\\meeting.mp4"
}
```

Do not use `file_url` for the main Laravel integration unless direct multipart
upload is not possible.

## Laravel Example

```php
$response = Http::withHeaders([
    'X-Internal-API-Key' => config('services.ai.internal_api_key'),
    'X-User-Id' => (string) auth()->id(),
    'X-User-Role' => auth()->user()->role ?? 'user',
])->attach(
    'file',
    fopen($upload->path, 'r'),
    $upload->original_name
)->post(config('services.ai.base_url') . '/api/v1/extractions/process-file', [
    'upload_id' => (string) $upload->id,
    'company_id' => (string) $upload->company_id,
    'project_id' => (string) $upload->project_id,
    'scope' => $upload->scope,
    'visibility' => $upload->visibility,
    'transcription_language' => $upload->isArabicMedia() ? 'ar' : null,
]);
```

## Laravel Persistence Contract

After a successful AI response, Laravel should save these fields on its own
upload/analysis tables:

```text
processing_status = processed
source_type
document_type
transcript
transcript_quality
summary
structured_summary
structured_result
decisions
decision_items
tasks
task_items
quality
warnings
indexed_chunk_count
processed_at
```

If the AI request fails, Laravel should save:

```text
processing_status = failed
processing_error = response body or exception message
```

Recommended background flow:

```text
1. Laravel stores the uploaded file.
2. Laravel creates upload record with processing_status=queued.
3. Laravel dispatches an upload-processing job.
4. The job sets processing_status=processing.
5. The job sends multipart file to /api/v1/extractions/process-file.
6. The job saves the AI response and sets processing_status=processed.
7. On non-2xx or exception, the job saves processing_status=failed.
```

## Retrieval API

Use this endpoint after uploads are indexed in Pinecone:

```http
POST /api/v1/retrieval/query
Content-Type: application/json
X-Internal-API-Key: <INTERNAL_API_KEY>
```

Request:

```json
{
  "project_id": "project-1",
  "company_id": "company-1",
  "scope": "project",
  "visibility": "members",
  "question": "What are the contract parties?",
  "top_k": 5
}
```

The AI service filters vector search by `project_id`, and when provided also by
`company_id`, `scope`, and `visibility`. Returned sources include metadata such
as `upload_id`, `document_type`, `chunk_index`, `source_id`, and `snippet`.

Recommended Laravel `.env` values:

```text
AI_SERVICE_BASE_URL=http://127.0.0.1:8001
AI_SERVICE_INTERNAL_API_KEY=<same value as ai-service INTERNAL_API_KEY>
```

## Notes

- The screenshot that shows `X-API-Key` and `Authorization: Bearer` does not match the current FastAPI code.
- Current FastAPI code expects `X-Internal-API-Key`.
- `Authorization: Bearer` is not required for backend-to-AI calls right now.
- `GROQ_API_KEY` is for AI transcription/LLM processing inside the AI service, not for the Laravel backend request header.
