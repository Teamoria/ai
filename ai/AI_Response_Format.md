# AI Response Format

## Objective

Define the standard JSON shape returned by AI insight endpoints or internal AI services. This format is designed for dashboard cards, API clients, and future persistence into the proposed `ai_insights` table.

## Schema

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `success` | boolean | Yes | Whether insight generation succeeded. |
| `insight_id` | integer/string/null | No | Persisted `ai_insights.id`, or null before persistence. |
| `title` | string | Yes | Short dashboard-ready title. |
| `type` | string | Yes | Insight type, such as `risk`, `recommendation`, `activity`, `workload`, or `processing_error`. |
| `severity` | string | Yes | `low`, `medium`, `high`, or `critical`. |
| `confidence_score` | number | Yes | Decimal from `0.00` to `1.00`. |
| `description` | string | Yes | Explanation of what the AI detected. |
| `recommendation` | string/object | No | Suggested action. Can be plain text or the structured recommendation format. |
| `related_entity` | object | No | Entity linked to the insight. |
| `sources` | array | Yes | Evidence sources used by the AI. |
| `created_at` | string | Yes | ISO 8601 timestamp. |

## Related Entity Format

```json
{
  "entity_type": "task",
  "entity_id": 901,
  "project_id": 88,
  "company_id": 12
}
```

Allowed `entity_type` values should include:

- `project`
- `task`
- `meeting`
- `knowledge_document`
- `user`
- `upload`

## Source Format

```json
{
  "source_type": "meeting_summary",
  "table": "meetings",
  "id": 73,
  "field": "summary",
  "snippet": "The payment integration remains blocked by missing credentials."
}
```

## Example JSON Response

```json
{
  "success": true,
  "insight_id": 501,
  "title": "Payment integration is blocked",
  "type": "risk",
  "severity": "high",
  "confidence_score": 0.91,
  "description": "The task is overdue and the latest meeting summary mentions missing credentials as a blocker.",
  "recommendation": {
    "action_title": "Escalate payment credentials",
    "reason": "The task cannot progress until production credentials are provided.",
    "priority": "high",
    "suggested_owner": {
      "user_id": 44,
      "name": "Project Manager"
    },
    "related_project_id": 88,
    "related_task_id": 901
  },
  "related_entity": {
    "entity_type": "task",
    "entity_id": 901,
    "project_id": 88,
    "company_id": 12
  },
  "sources": [
    {
      "source_type": "task",
      "table": "tasks",
      "id": 901,
      "field": "due_date",
      "snippet": "Due date is before today's date and status is in_progress."
    },
    {
      "source_type": "meeting_summary",
      "table": "meetings",
      "id": 73,
      "field": "summary",
      "snippet": "Payment integration is waiting for credentials."
    }
  ],
  "created_at": "2026-06-27T09:15:00Z"
}
```
