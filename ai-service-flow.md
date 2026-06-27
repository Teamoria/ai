# AI Service Flow

```text
Frontend Demo or PHP Backend
  -> FastAPI AI Service
      -> UploadProcessor
          -> save file
          -> detect source type
          -> extract text or transcribe media
          -> summarize with OpenAI
          -> save uploaded record
          -> index chunks in Pinecone when configured
          -> extract action items as tasks
      -> PostgreSQL

User question
  -> FastAPI AI Service
      -> AccessControlService builds user scope
      -> RagService loads visible records and tasks
      -> optional Pinecone search
      -> filter vector matches by visible record IDs
      -> LlmService produces grounded answer
```

## Backend Responsibilities

- `meetings/upload`: file processing and AI extraction.
- `tasks`: task review and status updates.
- `chat`: permission-aware workspace assistant.
- `auth`: simple JWT login for the demo and API testing.

## External Services

- Groq Whisper API for audio/video transcription.
- OpenAI Chat Completions for summaries and chatbot answers.
- Pinecone for optional vector search over summaries and transcripts.

## Integration With PHP

The PHP backend can treat this as an internal AI service:

```text
PHP receives user action
  -> sends file/message/task request to FastAPI
  -> receives JSON result
  -> stores or displays the result in the PHP platform
```

No PHP code needs to know how `ffmpeg`, Groq, OpenAI, or Pinecone are implemented internally.
