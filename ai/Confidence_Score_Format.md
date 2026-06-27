# Confidence Score Format

## Objective

Define how AI confidence scores are represented and interpreted across insights, recommendations, risk detection, and dashboard rules.

## Format

Confidence is a decimal number from `0.00` to `1.00`.

| Range | Label | Meaning |
| --- | --- | --- |
| `0.00-0.39` | Low confidence | Weak or incomplete evidence. The insight should be shown cautiously or require review. |
| `0.40-0.74` | Medium confidence | Useful evidence exists, but some assumptions or missing data remain. |
| `0.75-1.00` | High confidence | Strong evidence from structured records or multiple matching sources. |

## Scoring Guidance

| Evidence type | Suggested confidence |
| --- | --- |
| Direct structured rule, such as overdue due date | `0.85-0.98` |
| Multiple structured signals, such as overdue plus blocked status | `0.90-1.00` |
| Meeting summary mentions a blocker but no task status confirms it | `0.55-0.75` |
| Natural-language inference from transcript only | `0.45-0.70` |
| Missing or ambiguous source data | `0.20-0.45` |
| Failed processing or unsupported file type | `0.80-0.95` if the failure is explicitly captured |

## Rules

- Store confidence in `ai_insights.confidence_score` as a numeric decimal.
- Return confidence in API responses as a JSON number.
- Round to two decimal places for storage and display.
- Do not use percentages in API payloads.
- Dashboard UI may display `0.91` as `91%`, but the backend should keep `0.91`.

## Example Confidence Values

```json
[
  {
    "scenario": "Task due date is in the past and task is still in_progress",
    "confidence_score": 0.94,
    "confidence_label": "high"
  },
  {
    "scenario": "Meeting summary suggests a blocker but no linked task is found",
    "confidence_score": 0.62,
    "confidence_label": "medium"
  },
  {
    "scenario": "Transcript contains unclear language about possible delay",
    "confidence_score": 0.38,
    "confidence_label": "low"
  }
]
```

## Practical Example

An overdue task insight based only on `tasks.due_date` and `tasks.status` should receive high confidence because both signals are structured. A project-risk insight inferred only from a meeting transcript should receive lower confidence unless it is supported by task or project data.
