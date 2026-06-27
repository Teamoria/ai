# Teamoria AI Service API Contract

Base URL in Docker:

```text
http://localhost:8001/api/v1
```

All protected endpoints require:

```http
Authorization: Bearer <access_token>
```

## Login

```http
POST /auth/login
Content-Type: application/json
```

Request:

```json
{
  "email": "demo@teamoria.ai",
  "password": "demo-password"
}
```

Response:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "demo@teamoria.ai",
    "full_name": "System Admin",
    "system_role": "system_admin",
    "memberships": []
  }
}
```

## Upload And Process File

```http
POST /meetings/upload
Content-Type: multipart/form-data
```

Fields:

| Field | Required | Notes |
|---|---:|---|
| `file` | yes | audio, video, PDF, DOCX, text, markdown, CSV, SRT, VTT |
| `title` | no | optional display title |
| `document_type` | no | `auto`, `meeting`, `contract`, or `cv` |

Response:

```json
{
  "meeting": {
    "id": 12,
    "title": "Project Planning Meeting",
    "document_type": "meeting",
    "source_type": "video",
    "transcript": "...",
    "summary": "...",
    "created_at": "2026-06-23T10:30:00Z"
  },
  "tasks": [
    {
      "id": 44,
      "title": "Prepare UI prototype",
      "status": "pending_manager_review",
      "meeting_id": 12
    }
  ],
  "transcript": "...",
  "source_type": "video",
  "document_type": "meeting"
}
```

## List Uploaded Records

```http
GET /meetings/
```

Returns visible uploaded records for the authenticated user.

## List Tasks

```http
GET /tasks/
```

Returns visible tasks for the authenticated user.

## Approve Extracted Task

```http
POST /tasks/{task_id}/approve
Content-Type: application/json
```

Request:

```json
{
  "title": "Prepare UI prototype",
  "description": "Optional details",
  "assigned_to_user_id": null,
  "due_date": "2026-07-01"
}
```

The service changes the task status from `pending_manager_review` to `open`.

## Update Task

```http
PATCH /tasks/{task_id}
Content-Type: application/json
```

Request example:

```json
{
  "status": "done"
}
```

Allowed statuses:

```text
open, seen, in_progress, done, blocked, pending_manager_review
```

## Chat

```http
POST /chat/
Content-Type: application/json
```

Request:

```json
{
  "message": "What are the latest tasks?"
}
```

Response:

```json
{
  "answer": "..."
}
```

The chatbot uses only records and tasks visible to the authenticated user. Vector matches are filtered again by visible meeting IDs before being added to the LLM context.
