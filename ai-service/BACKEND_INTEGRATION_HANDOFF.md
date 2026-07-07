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

Process text or a Laravel-owned stored file:

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

Preferred Laravel-owned file URL:

```json
{
  "upload_id": "upload-1",
  "project_id": "project-1",
  "file_url": "https://backend.example.com/internal/uploads/upload-1/file"
}
```

If the Laravel file URL needs headers, configure `BACKEND_FILE_API_KEY`,
`BACKEND_FILE_API_KEY_HEADER`, or `BACKEND_FILE_BEARER_TOKEN` in `ai-service/.env`.

## Laravel Example

```php
$response = Http::withHeaders([
    'X-Internal-API-Key' => config('services.ai.internal_api_key'),
    'X-User-Id' => (string) auth()->id(),
    'X-User-Role' => auth()->user()->role ?? 'user',
])->post(config('services.ai.base_url') . '/api/v1/extractions/process', [
    'upload_id' => (string) $upload->id,
    'project_id' => (string) $upload->project_id,
    'file_url' => $internalFileUrl,
]);
```

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
