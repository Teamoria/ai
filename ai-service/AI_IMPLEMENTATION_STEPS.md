# Teamoria AI Sprint 1 - Implementation Plan

This document explains how the AI work will be implemented and integrated with the existing PHP backend.

The current backend is already running in PHP. The AI work should therefore be delivered as a separate internal AI service that exposes clear REST APIs to the PHP backend.

---

## Main Goal

Build an internal AI Service that supports:

- Workspace Chat with RAG.
- Meeting upload processing.
- Meeting summaries, decisions, and extracted tasks.
- Knowledge chunking and embeddings.
- Pinecone vector search.
- Agent workflow execution.
- Source citations and confidence scores.
- API contracts that the PHP backend can call.

The frontend should continue calling the PHP backend. The AI Service should not be called directly from the frontend.

---

## 0. System Integration With PHP Backend

The PHP backend remains the main application backend. It owns authentication, users, companies, projects, meetings, tasks, and frontend-facing APIs.

The AI Service receives scoped requests from the PHP backend and returns structured AI results.

```text
React Frontend
   |
   | REST / JSON
   v
PHP Backend
   |
   | Internal REST / JSON
   v
AI Service
   |
   | OpenAI / Pinecone / Whisper / MCP tools
   v
External AI Services
```

### PHP Backend Responsibilities

- Handle login and JWT authentication.
- Identify the current user.
- Decide which company, projects, meetings, and tasks the user can access.
- Store main business data.
- Receive frontend requests.
- Call the AI Service internally.
- Never expose the AI Service directly to the frontend.

### AI Service Responsibilities

- Receive requests only from the PHP backend.
- Validate internal API access.
- Use the scope sent by PHP.
- Run RAG chat.
- Process uploaded meetings and documents.
- Generate summaries, decisions, and tasks.
- Create knowledge chunks.
- Create embeddings and index them in Pinecone.
- Run agent workflows and log steps.
- Return clean JSON responses to PHP.

### Internal Authentication

The PHP backend should send an internal API key:

```http
X-Internal-Api-Key: internal_secret
```

The AI Service must reject any request without a valid internal key.

### Shared Request Shape

All AI endpoints should follow this structure:

```json
{
  "request_id": "uuid",
  "user": {
    "id": "user_uuid",
    "role": "member",
    "language": "en"
  },
  "scope": {
    "company_id": "company_uuid",
    "project_ids": ["project_uuid"],
    "visible_meeting_ids": ["meeting_uuid"]
  },
  "payload": {}
}
```

### Shared Success Response

```json
{
  "success": true,
  "data": {},
  "error": null,
  "request_id": "uuid"
}
```

### Shared Error Response

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "AI_NO_RELEVANT_DATA",
    "message": "No relevant information found",
    "details": {}
  },
  "request_id": "uuid"
}
```

---

## 1. Suggested File Structure

The AI Service can be implemented in Python with FastAPI. This structure keeps the AI code organized and easy to connect with the PHP backend.

```text
ai-service/
  app/
    main.py
    api/
      __init__.py
      deps.py
      v1/
        __init__.py
        router.py
        chat.py
        uploads.py
        agents.py
        sources.py
        workspace_graph.py
    core/
      __init__.py
      config.py
      database.py
      security.py
      errors.py
      logging.py
    models/
      __init__.py
      ai_chat.py
      knowledge.py
      meetings.py
      agents.py
      feedback.py
    schemas/
      __init__.py
      common.py
      chat.py
      upload.py
      meeting_intelligence.py
      knowledge.py
      agents.py
      sources.py
      errors.py
    services/
      __init__.py
      chat_service.py
      rag_service.py
      upload_processor.py
      meeting_intelligence_service.py
      knowledge_chunk_service.py
      embedding_service.py
      pinecone_service.py
      agent_service.py
      source_service.py
      workspace_graph_service.py
    clients/
      __init__.py
      openai_client.py
      pinecone_client.py
      whisper_client.py
      mcp_client.py
    utils/
      __init__.py
      chunking.py
      citations.py
      confidence.py
      retry.py
      file_extractors.py
    migrations/
      versions/
    tests/
      test_chat.py
      test_rag.py
      test_uploads.py
      test_agents.py
      test_permissions.py
    seeds/
      demo_data.py
  alembic.ini
  requirements.txt
  .env.example
  README.md
```

---

## 2. Folder Responsibilities

This section explains what each folder is for and what work needs to be done inside it.

### `ai-service/`

Root folder for the AI Service.

What we need to do here:

- Keep the full AI service codebase.
- Add project setup files.
- Add dependency files.
- Add environment examples.
- Add service documentation.

Expected files:

- `requirements.txt`
- `.env.example`
- `alembic.ini`
- `README.md`

### `app/`

Main application folder.

What we need to do here:

- Keep all Python application code.
- Keep API routes, services, models, schemas, and utilities together.
- Expose the FastAPI application from `main.py`.

### `app/api/`

API layer folder.

What we need to do here:

- Define HTTP endpoints.
- Validate incoming requests.
- Call the correct service.
- Return standardized JSON responses.
- Keep shared API dependencies in `deps.py`.

This folder should not contain heavy business logic. It should only route requests to services.

### `app/api/v1/`

Versioned API folder.

What we need to do here:

- Keep all version 1 endpoints.
- Group endpoints by feature.
- Register all endpoint files through `router.py`.

Main endpoint files:

- `chat.py` for RAG chat.
- `uploads.py` for meeting and file processing.
- `agents.py` for agent runs.
- `sources.py` for citation source details.
- `workspace_graph.py` for workspace graph data.

### `app/core/`

Core infrastructure folder.

What we need to do here:

- Configure environment variables.
- Configure database connection.
- Validate internal API key security.
- Define global error handling.
- Configure logging.

This folder contains application infrastructure, not AI business logic.

### `app/models/`

Database model folder.

What we need to do here:

- Define SQLAlchemy models.
- Map AI tables to Python classes.
- Define relationships between tables.
- Keep models clean and close to the database structure.

Main model groups:

- Chat models.
- Knowledge and embedding models.
- Meeting intelligence models.
- Agent run models.
- Feedback and source models.

### `app/schemas/`

Request and response schema folder.

What we need to do here:

- Define Pydantic schemas.
- Validate request bodies from PHP.
- Define response shapes returned to PHP.
- Keep API contracts stable and documented.

This folder is very important because PHP developers will depend on these request and response formats.

### `app/services/`

Business logic folder.

What we need to do here:

- Implement AI workflows.
- Coordinate database operations.
- Call external clients.
- Apply permission scope rules.
- Build final responses.

This is where most of the AI work happens.

Main service groups:

- Chat service.
- RAG service.
- Upload processor.
- Meeting intelligence service.
- Knowledge chunk service.
- Embedding service.
- Pinecone service.
- Agent service.
- Source service.
- Workspace graph service.

### `app/clients/`

External provider client folder.

What we need to do here:

- Wrap external services behind simple Python clients.
- Keep OpenAI, Pinecone, Whisper, and MCP logic separate from business services.
- Standardize provider errors.
- Make external calls easier to mock in tests.

Examples:

- `openai_client.py`
- `pinecone_client.py`
- `whisper_client.py`
- `mcp_client.py`

### `app/utils/`

Shared utility folder.

What we need to do here:

- Add reusable helper functions.
- Keep small logic that is used by multiple services.
- Avoid putting database or API route logic here.

Examples:

- Text chunking helpers.
- Citation formatting helpers.
- Confidence score helpers.
- Retry helpers.
- File extraction helpers.

### `migrations/`

Database migration folder.

What we need to do here:

- Store Alembic migrations.
- Track database changes.
- Create migration files for all AI tables.
- Keep migration history safe and reviewable.

### `migrations/versions/`

Migration version files folder.

What we need to do here:

- Store generated migration scripts.
- Add one migration for initial AI tables.
- Add future migrations when schemas change.

### `tests/`

Test folder.

What we need to do here:

- Test RAG logic.
- Test upload processing.
- Test permission filtering.
- Test agent workflow.
- Test API contracts.
- Mock external providers like OpenAI and Pinecone.

### `seeds/`

Demo data folder.

What we need to do here:

- Add demo company data.
- Add demo user scope.
- Add demo projects and meetings.
- Add demo chunks and chat sessions.
- Help frontend and PHP developers test without waiting for real data.

---

## 3. What Each File Contains

### `app/main.py`

Creates the FastAPI application.

Contains:

- FastAPI app instance.
- API router registration.
- Health check endpoint.
- Global exception handlers.
- Startup and shutdown hooks.

### `app/api/deps.py`

Shared API dependencies.

Contains:

- Internal API key validation dependency.
- Database session dependency.
- Request scope extraction.
- Common request validation helpers.

### `app/api/v1/router.py`

Main API router for version `v1`.

Contains:

- Imports all v1 route files.
- Registers routes under `/api/v1`.

### `app/api/v1/chat.py`

Chat and RAG endpoints.

Contains:

- `POST /api/v1/chat`
- `GET /api/v1/chat/sessions`
- Request validation.
- Calls to `ChatService` and `RagService`.

### `app/api/v1/uploads.py`

Upload processing endpoints.

Contains:

- `POST /api/v1/meetings/upload`
- `GET /api/v1/uploads/{id}/status`
- Calls to `UploadProcessor`.

### `app/api/v1/agents.py`

Agent workflow endpoints.

Contains:

- `POST /api/v1/agents/{agent_id}/runs`
- `GET /api/v1/agents/runs/{run_id}/steps`
- Calls to `AgentService`.

### `app/api/v1/sources.py`

Source detail endpoints.

Contains:

- `GET /api/v1/chat/sources/{id}`
- Returns source excerpt, metadata, timestamp, page number, and confidence.

### `app/api/v1/workspace_graph.py`

Workspace graph endpoint.

Contains:

- `GET /api/v1/workspace/graph`
- Calls to `WorkspaceGraphService`.

---

## 4. Core Files

### `app/core/config.py`

Application configuration.

Contains:

- Environment variable loading.
- Database URL.
- OpenAI key.
- Pinecone key and index name.
- Whisper provider config.
- Internal API key.
- Retry settings.

### `app/core/database.py`

Database setup.

Contains:

- SQLAlchemy engine.
- Session factory.
- Base model class.
- Database session helper.

### `app/core/security.py`

Internal service security.

Contains:

- `X-Internal-Api-Key` validation.
- Request scope validation.
- Helper to reject direct frontend access.

### `app/core/errors.py`

Standard error handling.

Contains:

- Custom AI exceptions.
- Error code constants.
- Error response builder.

Example error codes:

- `AI_VALIDATION_ERROR`
- `AI_PERMISSION_DENIED`
- `AI_NO_RELEVANT_DATA`
- `AI_EXTERNAL_SERVICE_FAILED`
- `AI_LOW_CONFIDENCE`
- `AI_PROCESSING_FAILED`

### `app/core/logging.py`

Logging setup.

Contains:

- Request logging.
- AI service logs.
- External provider error logs.
- Agent run logs.

---

## 5. Database Model Files

### `app/models/ai_chat.py`

Contains:

- `AIChatSession`
- `AIChatMessage`

Used for:

- Chat history.
- User questions.
- Assistant answers.
- Message citations.

### `app/models/knowledge.py`

Contains:

- `KnowledgeChunk`
- `Embedding`

Used for:

- Storing searchable text chunks.
- Linking chunks to Pinecone vector IDs.
- Tracking source type, source ID, company, project, and metadata.

### `app/models/meetings.py`

Contains:

- `MeetingSummary`
- `MeetingDecision`
- `ExtractedTask`

Used for:

- Meeting summaries.
- Key decisions.
- AI-generated task suggestions.

### `app/models/agents.py`

Contains:

- `AgentRun`
- `AgentRunStep`

Used for:

- Tracking every agent run.
- Logging tool calls.
- Storing inputs and outputs for each step.

### `app/models/feedback.py`

Contains:

- `AISource`
- `AIFeedback`

Used for:

- Source citation storage.
- User feedback on AI answers.

---

## 6. Schema Files

### `app/schemas/common.py`

Contains shared request and response schemas.

Examples:

- `UserContext`
- `AccessScope`
- `BaseAIRequest`
- `BaseAIResponse`

### `app/schemas/chat.py`

Contains:

- `ChatRequestPayload`
- `ChatRequest`
- `ChatResponse`
- `ChatSessionResponse`
- `ChatMessageResponse`

### `app/schemas/upload.py`

Contains:

- `UploadRequestPayload`
- `UploadRequest`
- `UploadStatusResponse`
- `ProcessingStatus`

### `app/schemas/meeting_intelligence.py`

Contains:

- `MeetingSummarySchema`
- `DecisionSchema`
- `ExtractedTaskSchema`
- `MeetingIntelligenceResult`

### `app/schemas/knowledge.py`

Contains:

- `KnowledgeChunkSchema`
- `EmbeddingMetadataSchema`

### `app/schemas/agents.py`

Contains:

- `AgentRunRequest`
- `AgentRunResponse`
- `AgentRunStepResponse`
- `ToolExecutionSchema`

### `app/schemas/sources.py`

Contains:

- `SourceCitation`
- `SourceDetailsResponse`

### `app/schemas/errors.py`

Contains:

- `AIError`
- `AIErrorResponse`

---

## 7. Service Files

### `app/services/chat_service.py`

Handles chat session and message persistence.

Contains:

- Create chat session.
- Save user message.
- Save assistant message.
- List chat sessions.
- Load chat history.

### `app/services/rag_service.py`

Handles the full RAG flow.

Contains:

- Query intake.
- Quick answer check.
- Intent detection.
- Pinecone retrieval.
- Permission filtering.
- Context assembly.
- Grounded answer generation.
- Language-aware response.

### `app/services/upload_processor.py`

Handles meeting and file processing.

Contains:

- Validate uploaded file metadata.
- Download or read file from internal storage.
- Extract text from documents.
- Transcribe audio.
- Store processing status.
- Trigger meeting intelligence.
- Trigger knowledge chunking and embeddings.

### `app/services/meeting_intelligence_service.py`

Turns meeting content into structured information.

Contains:

- Meeting summary generation.
- Key point extraction.
- Decision extraction.
- Task extraction.
- Confidence score checks.
- Saves summaries, decisions, and extracted tasks.

### `app/services/knowledge_chunk_service.py`

Creates knowledge chunks from text.

Contains:

- Chunk text into searchable pieces.
- Add chunk metadata.
- Save chunks to database.
- Prepare chunks for embedding.

### `app/services/embedding_service.py`

Creates embeddings.

Contains:

- Calls OpenAI embedding model.
- Builds embedding metadata.
- Sends vectors to Pinecone service.
- Saves embedding records.

### `app/services/pinecone_service.py`

Handles vector database operations.

Contains:

- Upsert vectors.
- Query vectors.
- Delete vectors by source.
- Namespace strategy per company.

### `app/services/agent_service.py`

Handles agent workflow.

Contains:

- Authorization.
- Run initialization.
- Context assembly.
- Intent classification.
- MCP tool execution.
- Step logging.
- Final synthesis.
- Run completion.

### `app/services/source_service.py`

Handles source lookup.

Contains:

- Get source by ID.
- Return source excerpt.
- Return source metadata.
- Validate source visibility.

### `app/services/workspace_graph_service.py`

Builds workspace relationship graph.

Contains:

- Project relationships.
- Meeting relationships.
- Task relationships.
- Graph nodes and edges.

---

## 8. External Client Files

### `app/clients/openai_client.py`

Contains:

- OpenAI chat completion calls.
- OpenAI embedding calls.
- Common response parsing.

### `app/clients/pinecone_client.py`

Contains:

- Pinecone client setup.
- Index connection.
- Query and upsert wrappers.

### `app/clients/whisper_client.py`

Contains:

- Audio transcription client.
- Groq Whisper integration if used.
- Transcription response parsing.

### `app/clients/mcp_client.py`

Contains:

- MCP tool call client.
- JSON-RPC request builder.
- Tool response parser.

---

## 9. Utility Files

### `app/utils/chunking.py`

Contains:

- Text splitting logic.
- Chunk size rules.
- Overlap rules.

### `app/utils/citations.py`

Contains:

- Citation formatter.
- Source excerpt builder.
- Citation confidence formatting.

### `app/utils/confidence.py`

Contains:

- Confidence score calculation.
- Low confidence rules.
- Review threshold logic.

### `app/utils/retry.py`

Contains:

- Retry wrapper for OpenAI, Pinecone, Whisper, and MCP.
- Max retry count.
- Backoff logic.

### `app/utils/file_extractors.py`

Contains:

- PDF text extraction.
- DOCX text extraction.
- TXT extraction.
- Audio file metadata helpers.

---

## 10. API Endpoints for PHP Backend

These endpoints are internal. PHP calls them. Frontend does not.

| Feature | Endpoint | Method |
|---|---|---|
| Upload Knowledge | `/api/v1/meetings/upload` | POST |
| Processing Status | `/api/v1/uploads/{id}/status` | GET |
| Workspace Chat | `/api/v1/chat` | POST |
| Chat History | `/api/v1/chat/sessions` | GET |
| Source Details | `/api/v1/chat/sources/{id}` | GET |
| Run Agent | `/api/v1/agents/{agent_id}/runs` | POST |
| Agent Run Steps | `/api/v1/agents/runs/{run_id}/steps` | GET |
| Workspace Graph | `/api/v1/workspace/graph` | GET |

---

## 11. Example: Workspace Chat API

Request from PHP to AI Service:

```http
POST /api/v1/chat
X-Internal-Api-Key: internal_secret
Content-Type: application/json
```

```json
{
  "request_id": "req_123",
  "user": {
    "id": "user_uuid",
    "role": "member",
    "language": "en"
  },
  "scope": {
    "company_id": "company_uuid",
    "project_ids": ["project_uuid"],
    "visible_meeting_ids": ["meeting_uuid"]
  },
  "payload": {
    "question": "What were the latest sprint decisions?",
    "session_id": "session_uuid"
  }
}
```

Response:

```json
{
  "success": true,
  "data": {
    "answer": "The latest decision was to use Pinecone as the vector database.",
    "citations": [
      {
        "source_id": "meeting_uuid",
        "source_type": "meeting",
        "title": "Sprint Planning Meeting",
        "excerpt": "Use Pinecone as vector database",
        "timestamp": "00:14:32",
        "confidence": 0.94
      }
    ],
    "confidence_score": 0.93,
    "language": "en"
  },
  "error": null,
  "request_id": "req_123"
}
```

---

## 12. Example: Upload Processing API

PHP receives the file from the frontend, stores it, then sends metadata to the AI Service.

```json
{
  "request_id": "req_456",
  "user": {
    "id": "user_uuid",
    "role": "admin",
    "language": "en"
  },
  "scope": {
    "company_id": "company_uuid",
    "project_ids": ["project_uuid"],
    "visible_meeting_ids": []
  },
  "payload": {
    "meeting_id": "meeting_uuid",
    "project_id": "project_uuid",
    "file_url": "https://internal-storage/files/meeting.mp3",
    "file_type": "audio",
    "title": "Sprint Planning Meeting"
  }
}
```

Response:

```json
{
  "success": true,
  "data": {
    "upload_id": "upload_uuid",
    "status": "queued"
  },
  "error": null,
  "request_id": "req_456"
}
```

---

## 13. Example: Agent Run API

Request:

```json
{
  "request_id": "req_789",
  "user": {
    "id": "user_uuid",
    "role": "manager",
    "language": "en"
  },
  "scope": {
    "company_id": "company_uuid",
    "project_ids": ["project_uuid"],
    "visible_meeting_ids": ["meeting_uuid"]
  },
  "payload": {
    "agent_id": "agent_uuid",
    "instruction": "Give me the project status and overdue tasks.",
    "allowed_tools": ["list_tasks", "get_project_status", "search_meetings"]
  }
}
```

Response:

```json
{
  "success": true,
  "data": {
    "run_id": "run_uuid",
    "status": "completed",
    "result": {
      "answer": "The project is moving, but there are 3 overdue tasks.",
      "used_tools": ["list_tasks", "get_project_status"]
    }
  },
  "error": null,
  "request_id": "req_789"
}
```

---

## 14. Database Tables

Required AI tables:

- `ai_chat_sessions`
- `ai_chat_messages`
- `knowledge_chunks`
- `embeddings`
- `meeting_summaries`
- `meeting_decisions`
- `extracted_tasks`
- `ai_sources`
- `ai_feedback`
- `agent_runs`
- `agent_run_steps`

These tables can live in the same PostgreSQL database if the team agrees, or in a separate AI database. The important part is that IDs from PHP tables are passed clearly to the AI Service.

---

## 15. Implementation Order

Recommended order:

1. Create AI Service project structure.
2. Add environment config.
3. Add internal API key validation.
4. Add database connection.
5. Create SQLAlchemy models.
6. Create migrations.
7. Create Pydantic schemas.
8. Build shared request and response contracts.
9. Build chat and RAG services.
10. Build knowledge chunking.
11. Build embedding and Pinecone integration.
12. Build upload processing.
13. Build meeting intelligence.
14. Build agent workflow.
15. Add source citation service.
16. Add error handling.
17. Add tests.
18. Add demo seed data.
19. Test PHP-to-AI integration.
20. Run end-to-end flow.

---

## 16. End-to-End Flow

Final expected flow:

1. User sends a request from frontend.
2. PHP backend authenticates the user.
3. PHP backend builds user scope.
4. PHP backend calls the AI Service.
5. AI Service validates the internal API key.
6. AI Service runs the needed AI workflow.
7. AI Service filters all data by the provided scope.
8. AI Service returns structured JSON.
9. PHP backend returns the final response to frontend.

---

## 17. Definition of Done

Sprint 1 is complete when:

- The AI Service has a clear file structure.
- Internal PHP-to-AI authentication is implemented.
- Shared request and response contracts are implemented.
- AI database models and migrations exist.
- RAG chat returns answers with citations.
- Meeting upload processing is available.
- Meeting summaries, decisions, and task extraction work.
- Pinecone indexing and retrieval work.
- Agent workflow logs each step.
- Permission scope is applied before returning any AI result.
- Basic tests pass.
- PHP backend can call the AI Service successfully.
