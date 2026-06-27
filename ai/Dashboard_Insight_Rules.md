# Dashboard Insight Rules

## Objective

Define the rules used to generate dashboard insights from the existing Teamoria data model. These rules transform data from `projects`, `tasks`, `meetings`, `knowledge_documents`, and related file tables into actionable AI insight cards.

## Design

```mermaid
flowchart LR
    P[projects] --> R[Rule Engine]
    T[tasks] --> R
    M[meetings.summary] --> R
    K[knowledge_documents] --> R
    F[meeting_files / task_files] --> R
    R --> I[ai_insights]
    I --> D[Dashboard]
```

## Rules

| Rule name | Condition | Insight type | Severity | Suggested recommendation |
| --- | --- | --- | --- | --- |
| `overdue_task` | `tasks.due_date < today` and `tasks.status not in ('done')` | `risk` | `high` if overdue by 3+ days, otherwise `medium` | Ask the assignee for a status update, adjust the due date, or reassign support. |
| `inactive_project` | No project-related task, meeting, or knowledge update for 7+ days while `projects.status = 'active'` | `activity` | `medium` at 7 days, `high` at 14+ days | Schedule a project review and confirm whether the project is still active. |
| `delayed_project_progress` | Project has active tasks but completion ratio is below expected progress based on deadline | `progress` | `medium` or `high` based on delay size | Reprioritize blockers and split large tasks into smaller owner-specific actions. |
| `missing_task_updates` | `tasks.status in ('open', 'in_progress', 'blocked')` and no recent `task_notes` or meeting updates mention the task | `activity` | `medium` | Request a written update from the owner before the next standup. |
| `high_workload_team_member` | A user has more than the configured threshold of open or in-progress tasks | `workload` | `medium` or `high` based on count and overdue tasks | Move lower-priority work to another member or defer it. |
| `failed_upload_or_ai_processing` | `knowledge_documents.status in ('failed', 'processing_failed')` or upload processing raises an unsupported/empty-content error | `processing_error` | `high` | Re-upload a supported file, check parsing dependencies, or retry processing. |

## Rule Details

### Overdue Tasks

- Source: `tasks`.
- Uses: `due_date`, `status`, `priority`, `assigned_to_user_id`, `project_id`, `organization_id`.
- Recommended severity:
  - `medium`: 1-2 days overdue.
  - `high`: 3-7 days overdue.
  - `critical`: more than 7 days overdue or priority is high and the task blocks other tasks.

### Inactive Projects

- Source: `projects`, `tasks`, `meetings`, `knowledge_documents`.
- A project is considered inactive when there is no recent activity linked to `project_id`.
- Activity can include task creation, meeting creation, meeting upload, or knowledge document creation.

### Delayed Project Progress

- Source: `projects`, `tasks`.
- Completion ratio:

```text
completed_tasks_count / total_tasks_count
```

- Expected progress can be estimated from elapsed project time:

```text
days_since_start / total_project_days
```

### Missing Task Updates

- Source: `tasks`, `task_notes`, `meetings`.
- This project currently has `task_notes` in `backend/app/models/erd_extensions.py`.
- A missing update should be generated only for visible, active tasks.

### High Workload

- Source: `tasks`, `users`.
- Count active tasks where `assigned_to_user_id = users.id` and status is `open`, `in_progress`, `blocked`, or `pending_manager_review`.

### Failed Upload or AI Processing

- Source: `knowledge_documents.status` and upload processing failures in `UploadProcessor`.
- Current upload flow creates meetings and indexes summaries through `VectorStore`; it does not yet persist all upload failures.

## Example Insight

```json
{
  "title": "Project has had no updates for 10 days",
  "type": "activity",
  "severity": "medium",
  "description": "The project is active, but no linked tasks, meetings, or knowledge documents were updated recently.",
  "recommendation": "Schedule a short project review and confirm current blockers with the project manager.",
  "confidence_score": 0.84,
  "metadata": {
    "rule": "inactive_project",
    "inactive_days": 10,
    "project_id": 88
  }
}
```
