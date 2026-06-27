# Recommendation Format

## Objective

Define the standard structure for AI recommendations so they can be displayed on the dashboard, stored inside `ai_insights.recommendation`, or returned by AI APIs.

## Schema

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `action_title` | string | Yes | Short action the user should take. |
| `reason` | string | Yes | Why the recommendation is being made. |
| `priority` | string | Yes | `low`, `medium`, `high`, or `critical`. |
| `suggested_owner` | object/null | No | User who should own the action. |
| `related_project_id` | integer/null | No | Linked `projects.id`. |
| `related_task_id` | integer/null | No | Linked `tasks.id`. |
| `related_meeting_id` | integer/null | No | Linked `meetings.id` when generated from a meeting summary. |
| `expected_outcome` | string | No | Expected result after the action is completed. |
| `due_by` | date/null | No | Suggested target date for the recommendation. |

## Rules

- Use a direct action title, not a vague summary.
- Choose `suggested_owner` from `users` when the owner can be inferred from `tasks.assigned_to_user_id`, `projects.created_by_user_id`, or project membership.
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
  "related_meeting_id": 73,
  "expected_outcome": "The task owner receives support and the blocker is removed within one working day.",
  "due_by": "2026-06-28"
}
```

## Practical Example

If a task is overdue and assigned to a team member with too many active tasks, the recommendation should suggest either reassignment or adding support. The recommendation should not simply say "task is overdue"; that belongs in the insight description.
