# Project Metadata Schema

## Objective

Define the project-level metadata that AI services should compute before generating risks, recommendations, and dashboard insights. The metadata is derived from the current `projects`, `tasks`, `meetings`, `project_members`, and `knowledge_documents` tables.

## Schema

| Field | Type | Source | Description |
| --- | --- | --- | --- |
| `project_id` | integer | `projects.id` | Project identifier. |
| `company_id` | integer | `projects.organization_id` | Tenant/company identifier. |
| `progress` | number | Derived from `tasks.status` | Completion ratio from `0.00` to `1.00`. |
| `status` | string | `projects.status` | Current project status, such as `active`, `paused`, or `completed`. |
| `priority` | string | Derived or configured | Project priority. If absent on `projects`, derive from task priorities. |
| `deadline` | date | `projects.end_date` | Target completion date. |
| `team_size` | integer | `project_members` | Number of users linked to the project. |
| `overdue_tasks_count` | integer | `tasks` | Count of incomplete tasks with due dates before today. |
| `completed_tasks_count` | integer | `tasks` | Count of tasks where `status = 'done'`. |
| `total_tasks_count` | integer | `tasks` | Total tasks linked to the project. |
| `inactive_days` | integer | Derived | Days since the latest linked task, meeting, or document activity. |
| `risk_level` | string | Derived | `low`, `medium`, `high`, or `critical`. |

## Calculation Rules

```text
progress = completed_tasks_count / total_tasks_count
```

If `total_tasks_count = 0`, use `progress = 0.00` and add `metadata.no_tasks = true`.

```text
inactive_days = today - max(project.updated_at, latest_task.created_at, latest_meeting.created_at, latest_document.created_at)
```

## Example JSON Metadata

```json
{
  "project_id": 88,
  "company_id": 12,
  "progress": 0.42,
  "status": "active",
  "priority": "high",
  "deadline": "2026-07-15",
  "team_size": 6,
  "overdue_tasks_count": 4,
  "completed_tasks_count": 8,
  "total_tasks_count": 19,
  "inactive_days": 5,
  "risk_level": "high",
  "metadata": {
    "latest_activity_source": "tasks",
    "latest_activity_at": "2026-06-22T14:40:00Z",
    "derived_priority_reason": "2 high-priority tasks are overdue"
  }
}
```

## Practical Example

A project has 19 tasks. Eight are done, four are overdue, and the deadline is 18 days away. The AI metadata service computes `progress = 0.42` and `risk_level = high` because the project has meaningful remaining work plus overdue high-priority tasks.
