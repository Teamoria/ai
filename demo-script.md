# Demo Script

Use this sequence to present the AI service clearly.

## 1. Start The Service

```bash
docker compose up --build
```

Open:

```text
http://localhost:5174
```

## 2. Login

Use:

```text
demo@teamoria.ai
demo-password
```

The first login creates the first demo user automatically.

## 3. Upload A Meeting Source

Upload one of:

- short meeting audio/video
- `.txt` meeting notes
- `.pdf` meeting minutes
- `.docx` meeting notes

Show that the service returns:

- source type
- document type
- transcript
- summary
- extracted tasks

## 4. Review Tasks

Go to the Tasks tab.

Show:

- extracted tasks start as `pending_manager_review`
- task can be approved
- task status can be changed to `in_progress` or `done`

## 5. Ask The Chatbot

Go to the Chat tab.

Suggested questions:

```text
What are the latest uploaded records?
What are the latest tasks?
Summarize the last meeting.
Which tasks are still open?
```

Arabic examples:

```text
ما آخر المهام؟
لخص آخر اجتماع
ما المهام غير المنجزة؟
```

## 6. Handoff Message

Say:

```text
This folder is the standalone AI service. The PHP backend can call it using REST APIs.
It owns upload processing, transcription, summarization, task extraction, and RAG chat.
```
