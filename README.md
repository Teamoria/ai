# Teamoria Backend

Backend workspace for Teamoria.

This repository includes the FastAPI AI Service structure for Teamoria.

The AI work will be implemented with FastAPI. The main backend is implemented in PHP and remains responsible for authentication, users, companies, projects, meetings, tasks, and frontend-facing APIs.

The FastAPI AI Service is an internal service. It exposes REST APIs that the PHP backend can call for AI features.

## Project Structure

```text
.
+-- ai-service/
|   +-- app/
|   |   +-- api/
|   |   +-- clients/
|   |   +-- core/
|   |   +-- models/
|   |   +-- schemas/
|   |   +-- services/
|   |   +-- tests/
|   |   +-- utils/
|   +-- .env.example
|   +-- alembic.ini
|   +-- AI_IMPLEMENTATION_STEPS.md
|   +-- requirements.txt
|   +-- README.md
+-- index.html
+-- package.json
```

## FastAPI AI Service Scope

The FastAPI AI Service will support:

- Workspace chat with RAG.
- Meeting upload processing.
- Meeting summaries, decisions, and extracted tasks.
- Knowledge chunking and embeddings.
- Pinecone vector search.
- Agent workflow execution.
- Source citations and confidence scores.
- Internal API contracts for the PHP backend.

## Integration Flow

```text
React Frontend
   |
   v
PHP Backend
   |
   v
FastAPI AI Service
   |
   v
OpenAI / Pinecone / Whisper / MCP tools
```

The frontend should call the PHP backend only. The PHP backend calls the FastAPI AI Service internally using REST/JSON and an internal API key.

## Documentation

See [ai-service/AI_IMPLEMENTATION_STEPS.md](ai-service/AI_IMPLEMENTATION_STEPS.md) for the full implementation plan, file structure, API contracts, and Sprint 1 checklist.
