# Risk Detection Logic

## Objective

Define how Teamoria AI detects project and task risk using the existing project, task, meeting, and upload data. The goal is to produce consistent risk levels that can feed dashboard insights and recommendations.

## Inputs

| Input | Source | Notes |
| --- | --- | --- |
| Project status | `project.status` | Only active projects should generate active risk warnings. |
| Project deadline | `project.end_date` | Used for schedule pressure. |
| Task due date | `task.due_date` | Used for overdue and upcoming-deadline risk. |
| Task status | `task.status` | Open, in-progress, blocked, pending review, or done. |
| Task priority | `task.priority` | Used to increase risk when important work is delayed. |
| Meeting summary | `meeting_summary` | Used to detect blockers mentioned in natural language. |
| Activity timestamps | `project.updated_at`, `task.created_at`, `meeting_summary.created_at`, `upload.created_at` | Used for inactivity risk. |

## Risk Levels

| Risk level | Meaning | Typical triggers |
| --- | --- | --- |
| `low` | Normal monitoring. | No overdue work, recent activity, progress roughly matches timeline. |
| `medium` | Needs attention soon. | Minor overdue work, 7+ inactive days, or progress slightly behind expected pace. |
| `high` | Needs manager action. | Multiple overdue tasks, blocked high-priority work, or major progress delay. |
| `critical` | Immediate escalation. | Deadline is near or passed, critical task is blocked/overdue, or many tasks are overdue. |

## Calculation Rules

### Task Risk

Start with a score of `0`.

| Condition | Score impact |
| --- | --- |
| Task is overdue by 1-2 days | `+20` |
| Task is overdue by 3-7 days | `+35` |
| Task is overdue by more than 7 days | `+50` |
| Task status is `blocked` | `+30` |
| Task priority is `high` or `critical` | `+15` |
| Task is assigned to a user with high workload | `+10` |
| Latest meeting summary mentions a blocker for the task | `+15` |

Task risk level:

| Score | Risk level |
| --- | --- |
| `0-24` | `low` |
| `25-49` | `medium` |
| `50-74` | `high` |
| `75+` | `critical` |

### Project Risk

Project risk combines schedule pressure, overdue tasks, progress delay, and inactivity.

```text
completion_ratio = completed_tasks_count / total_tasks_count
expected_ratio = elapsed_project_days / total_project_days
progress_gap = expected_ratio - completion_ratio
```

Score impacts:

| Condition | Score impact |
| --- | --- |
| `overdue_tasks_count >= 1` | `+15` |
| `overdue_tasks_count >= 3` | `+25` |
| `overdue_tasks_count >= 6` | `+40` |
| `progress_gap >= 0.15` | `+20` |
| `progress_gap >= 0.30` | `+35` |
| `inactive_days >= 7` | `+15` |
| `inactive_days >= 14` | `+30` |
| Deadline in 7 days and progress below `0.80` | `+30` |
| Deadline passed and project is still active | `+50` |

## Example Calculation

Task example:

```json
{
  "task_id": 901,
  "status": "blocked",
  "priority": "high",
  "days_overdue": 5,
  "workload_status": "high",
  "meeting_blocker_detected": true
}
```

Score:

```text
35 overdue by 3-7 days
+30 blocked
+15 high priority
+10 high workload
+15 meeting blocker
= 105
```

Risk level: `critical`.

## Practical Output

```json
{
  "risk_level": "critical",
  "risk_score": 105,
  "drivers": [
    "Task is 5 days overdue",
    "Task is blocked",
    "Task has high priority",
    "Assignee has high workload",
    "Latest meeting summary mentions a blocker"
  ]
}
```
