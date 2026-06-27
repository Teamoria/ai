# AI Insights Data Model

## Objective

Define the proposed storage model for AI-generated insights without duplicating existing Teamoria tables. The current codebase already stores users, projects, tasks, meetings, decisions, uploaded knowledge documents, and knowledge chunks. The `ai_insights` table should act as a normalized output layer that links AI findings back to those existing records.

## Current Codebase Mapping

| Business concept | Current table/model |
| --- | --- |
| Company / tenant | `organizations` |
| User | `users` |
| Project | `projects` |
| Task | `tasks` |
| Meeting summary | `meetings.summary` |
| Extracted decisions | `decisions` |
| Uploaded documents | `knowledge_documents`, `meeting_files`, `task_files` |
| Knowledge chunks | `knowledge_chunks` |

Note: this project does not currently contain an `ai_insights` model/table. It also does not contain separate `meeting_summaries`, `extracted_decisions`, or `uploads` tables by those exact names.

## Proposed Schema

Table name: `ai_insights`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | integer / bigint | Yes | Primary key. |
| `company_id` | integer | Yes | References `organizations.id`. Named `company_id` for product language; maps to organization internally. |
| `user_id` | integer | No | References `users.id`; the user who triggered or owns the insight. |
| `project_id` | integer | No | References `projects.id` when the insight is project-related. |
| `task_id` | integer | No | References `tasks.id` when the insight is task-related. |
| `meeting_summary_id` | integer | No | References `meetings.id`; the summary is stored in `meetings.summary`. |
| `upload_id` | integer | No | References `knowledge_documents.id` for uploaded knowledge sources. For meeting/task files, store the table name in `metadata.source_table`. |
| `title` | varchar(255) | Yes | Human-readable insight title. |
| `type` | varchar(60) | Yes | Insight category, such as `risk`, `recommendation`, `workload`, `progress`, `processing_error`. |
| `severity` | varchar(40) | Yes | `low`, `medium`, `high`, or `critical`. |
| `description` | text | Yes | AI-readable and user-readable explanation. |
| `recommendation` | text | No | Suggested action. |
| `confidence_score` | numeric(4,2) | Yes | Decimal value from `0.00` to `1.00`. |
| `status` | varchar(40) | Yes | `new`, `acknowledged`, `in_progress`, `resolved`, `dismissed`. |
| `metadata` | json/jsonb | No | Extra evidence, rule name, source snippets, risk inputs, or processing details. |
| `created_at` | timestamp | Yes | Creation timestamp. |
| `updated_at` | timestamp | Yes | Last update timestamp. |

## Relationships

```mermaid
erDiagram
    organizations ||--o{ ai_insights : owns
    users ||--o{ ai_insights : triggers
    projects ||--o{ ai_insights : relates_to
    tasks ||--o{ ai_insights : relates_to
    meetings ||--o{ ai_insights : generated_from_summary
    knowledge_documents ||--o{ ai_insights : generated_from_upload
```

## Rules

- Do not create duplicate meeting summary storage. Use `meetings.summary`.
- Do not create duplicate decision storage. Use `decisions`.
- Use `knowledge_documents` as the primary uploaded-document reference when the source is a knowledge upload.
- Use `metadata.source_table` and `metadata.source_id` when the source is `meeting_files` or `task_files`.
- One insight may reference multiple evidence sources inside `metadata.sources` even if the core relational fields point to the primary source.

## Example Record

```json
{
  "id": 501,
  "company_id": 12,
  "user_id": 44,
  "project_id": 88,
  "task_id": 901,
  "meeting_summary_id": 73,
  "upload_id": null,
  "title": "Payment integration task is overdue",
  "type": "risk",
  "severity": "high",
  "description": "The task is 5 days past its due date and is still marked in_progress.",
  "recommendation": "Reassign a backup engineer and ask the current owner for a same-day status update.",
  "confidence_score": 0.91,
  "status": "new",
  "metadata": {
    "rule": "overdue_task",
    "source_table": "tasks",
    "source_id": 901,
    "days_overdue": 5,
    "task_status": "in_progress"
  },
  "created_at": "2026-06-27T09:15:00Z",
  "updated_at": "2026-06-27T09:15:00Z"
}
```
