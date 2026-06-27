# Recommendation Format

## Objective

Define the standard structure for AI recommendations so they can be displayed on the dashboard, returned by AI APIs, or stored later if the ERD adds an AI insight table.

## Schema

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `action_title` | string | Yes | Short action the user should take. |
| `reason` | string | Yes | Why the recommendation is being made. |
| `priority` | string | Yes | `low`, `medium`, `high`, or `critical`. |
| `suggested_owner` | object/null | No | User who should own the action. |
| `related_project_id` | integer/null | No | Linked `project.id`. |
| `related_task_id` | integer/null | No | Linked `task.id`. |
| `related_meeting_summary_id` | integer/null | No | Linked `meeting_summary.id` when generated from a meeting summary. |
| `expected_outcome` | string | No | Expected result after the action is completed. |
| `due_by` | date/null | No | Suggested target date for the recommendation. |

## Rules

- Use a direct action title, not a vague summary.
- Choose `suggested_owner` from `user` when the owner can be inferred from `task.assigned_to_user_id`, `project.created_by_user_id`, or `project_user`.
- Keep `reason` evidence-based and link it to the underlying task, project, meeting, or upload.
- Use `critical` only when delay or failure is likely to harm the sprint goal.

## Example Recommendation JSON

```json
{
  "action_title": "Reassign backend support for payment integration",
  "reason": "The payment integration task is blocked, high priority, and 5 days overdue.",
  "priority": "critical",
  "suggested_owner": {
    "user_id": 44,
    "name": "Sara Ahmad",
    "role": "project_manager"
  },
  "related_project_id": 88,
  "related_task_id": 901,
  "related_meeting_summary_id": 73,
  "expected_outcome": "The task owner receives support and the blocker is removed within one working day.",
  "due_by": "2026-06-28"
}
```

## Practical Example

If a task is overdue and assigned to a team member with too many active tasks, the recommendation should suggest either reassignment or adding support. The recommendation should not simply say "task is overdue"; that belongs in the insight description.
