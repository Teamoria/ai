# AI Processing Workflow

## Objective

Document the full AI workflow from file upload to dashboard insights. This workflow follows the current FastAPI service structure, especially `UploadProcessor`, `MeetingRepository`, `TaskRepository`, `VectorStore`, `RagService`, and the existing database models.

## Current Workflow

```mermaid
flowchart TD
    A[User uploads file to /meetings/upload] --> B[UploadProcessor saves file]
    B --> C[Detect source type: text, audio, video]
    C --> D[Extract text or transcribe media]
    D --> E[Detect document type]
    E --> F[Generate summary with LlmService]
    F --> G[Create meetings record]
    G --> H[Index summary and transcript chunks in VectorStore]
    G --> I[Extract action items with TaskExtractor]
    I --> J[Create tasks with pending_manager_review]
    H --> K[Chat and RAG can search indexed content]
    J --> L[Manager reviews tasks]
    G --> M[Future insight rules generate ai_insights]
    J --> M
    M --> N[Recommendations]
    N --> O[Dashboard]
```

## Target Workflow With Insights

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI AI Service
    participant Upload as UploadProcessor
    participant DB as PostgreSQL
    participant LLM as LlmService
    participant Vector as VectorStore
    participant Rules as Insight Rule Engine
    participant Dashboard

    User->>API: Upload meeting/document
    API->>Upload: process(file, project_id, organization_id)
    Upload->>DB: Save meeting transcript and summary
    Upload->>LLM: Summarize transcript
    Upload->>DB: Create tasks from extracted action items
    Upload->>Vector: Index summary/transcript chunks
    Rules->>DB: Read projects, tasks, meetings, knowledge_documents
    Rules->>Rules: Detect risks, workload, inactivity, processing failures
    Rules->>DB: Store ai_insights
    Dashboard->>DB: Read ai_insights and related entities
    Dashboard-->>User: Show insights and recommendations
```

## Stages

| Stage | Current implementation | Output |
| --- | --- | --- |
| Upload | `backend/app/api/v1/meetings.py` and `UploadProcessor` | Saved file and processed text. |
| Processing | `UploadProcessor._detect_source_type`, `_extract_text`, `_detect_document_type` | Source type and document type. |
| Transcript / text extraction | `Transcriber` for media, file readers for text/PDF/DOCX | Transcript text. |
| Summary | `LlmService.summarize` | `meetings.summary`. |
| Chunking | `VectorStore._meeting_documents` chunks transcript every 1600 characters | Vector-ready summary/transcript chunks. |
| Embedding / vector indexing | `VectorStore.index_meeting` | Pinecone records when configured. |
| Task extraction | `TaskExtractor.extract` | `tasks` with `pending_manager_review`. |
| Insights | Proposed rule engine | `ai_insights`. |
| Recommendations | Proposed recommendation generator | Structured recommendation JSON. |
| Dashboard | Future UI/API consumer | Insight cards, risk panels, workload warnings. |

## Fields and Rules

- Meeting summaries should continue to use `meetings.summary`.
- Extracted decisions should continue to use `decisions`.
- Uploaded knowledge files should use `knowledge_documents`.
- Meeting upload artifacts can use `meeting_files`.
- Task attachments can use `task_files`.
- Knowledge chunks should use `knowledge_chunks`.
- New AI insight output should be stored in the proposed `ai_insights` table only if persistence is required.

## Practical Example

1. A manager uploads a meeting recording.
2. The service transcribes it and stores the transcript in `meetings.transcript`.
3. The AI summary is stored in `meetings.summary`.
4. Action items become `tasks` with `pending_manager_review`.
5. The summary and transcript are indexed in Pinecone through `VectorStore`.
6. The insight rules detect that one extracted task is high priority and overdue.
7. The recommendation generator suggests assigning a backup owner.
8. The dashboard displays a high-severity insight linked to the task and meeting.
