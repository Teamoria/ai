"""Meeting summary, decision, and task extraction service."""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

from app.clients.groq_client import GroqLlmClient
from app.core.config import settings


class MeetingIntelligenceService:
    """Extract meeting intelligence from text without owning persistence."""

    def __init__(self, llm_client: GroqLlmClient | None = None) -> None:
        self.llm_client = llm_client or GroqLlmClient()

    def analyze(self, transcript: str) -> dict[str, Any]:
        clean_transcript = self._normalize_text(transcript)
        transcript_quality = self.assess_transcript_quality(clean_transcript)
        if settings.llm_provider.lower() == "groq" and settings.groq_api_key:
            result = self._analyze_with_groq(clean_transcript)
            if not result["task_items"]:
                result["task_items"] = self.extract_task_items(clean_transcript)
                result["tasks"] = [item["title"] for item in result["task_items"]]
            if not result["structured_summary"].get("overview"):
                result["structured_summary"] = self.build_structured_summary(
                    clean_transcript,
                    result["decision_items"],
                    result["task_items"],
                )
                result["summary"] = self.summary_text(result["structured_summary"])
            result["transcript_quality"] = transcript_quality
            return self._normalize_result(result)

        decision_items = self.extract_decision_items(clean_transcript)
        task_items = self.extract_task_items(clean_transcript)
        structured_summary = self.build_structured_summary(clean_transcript, decision_items, task_items)

        return self._normalize_result(
            {
                "summary": self.summary_text(structured_summary),
                "structured_summary": structured_summary,
                "transcript_quality": transcript_quality,
                "decisions": [self._legacy_decision_text(item) for item in decision_items],
                "decision_items": decision_items,
                "tasks": [item["title"] for item in task_items],
                "task_items": task_items,
            },
        )

    def summarize(self, transcript: str) -> str:
        clean_transcript = self._normalize_text(transcript)
        decision_items = self.extract_decision_items(clean_transcript)
        task_items = self.extract_task_items(clean_transcript)
        return self.summary_text(self.build_structured_summary(clean_transcript, decision_items, task_items))

    def summary_text(self, structured_summary: dict[str, Any]) -> str:
        parts = []
        if structured_summary.get("title"):
            parts.append(str(structured_summary["title"]))
        parts.append(str(structured_summary.get("overview") or ""))
        if structured_summary.get("priority"):
            parts.append(f"Priority: {structured_summary['priority']}")
        return "\n\n".join(part for part in parts if part.strip())

    def build_structured_summary(
        self,
        transcript: str,
        decision_items: list[dict[str, Any]],
        task_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        transcript_quality = self.assess_transcript_quality(transcript)
        if transcript_quality["level"] == "low":
            return {
                "title": "Low quality transcript",
                "overview": (
                    "The extracted transcript is too short, repetitive, or unclear to produce a reliable meeting summary. "
                    "Please review the transcript and retry with clearer audio or a written transcript if this meeting is important."
                ),
                "priority": None,
                "key_points": ["Transcript quality is low"],
                "task_count": len(task_items),
                "decision_count": len(decision_items),
            }

        summary_source = self._remove_task_sections(transcript)
        sentences = self._sentences(summary_source)
        overview = self._build_overview(sentences, decision_items, task_items)

        key_points = []
        if decision_items:
            key_points.append(f"{len(decision_items)} decision(s) extracted")
        if task_items:
            key_points.append(f"{len(task_items)} actionable task(s) extracted")

        return {
            "title": self._extract_title(transcript),
            "overview": overview[:1000],
            "priority": self._extract_priority(transcript),
            "key_points": key_points,
            "task_count": len(task_items),
            "decision_count": len(decision_items),
        }

    def assess_transcript_quality(self, transcript: str) -> dict[str, Any]:
        words = re.findall(r"[\w\u0600-\u06ff]+", transcript or "", flags=re.UNICODE)
        word_count = len(words)
        unique_word_ratio = round(len({word.casefold() for word in words}) / max(word_count, 1), 2)
        repeated_phrases = self._repeated_phrase_count(transcript)
        has_media_noise = self._looks_like_media_noise(transcript.casefold())
        score = 100
        if word_count < 20:
            score -= 45
        elif word_count < 50:
            score -= 25
        if unique_word_ratio < 0.45:
            score -= 25
        if repeated_phrases >= 2:
            score -= 20
        if has_media_noise:
            score -= 65
        if len(transcript.strip()) < 80:
            score -= 15
        score = max(0, min(100, score))
        level = "high" if score >= 75 else "medium" if score >= 45 else "low"
        warning = None
        suggestions: list[str] = []
        if level == "low":
            warning = "The transcript looks too short or unclear for a reliable AI summary."
            suggestions = [
                "Use audio/video with clearer speech and less background noise.",
                "Keep the speaker close to the microphone.",
                "For Arabic videos, send transcription_language=ar or set GROQ_TRANSCRIPTION_LANGUAGE=ar.",
                "Upload a written transcript or captions file when available.",
            ]
        elif level == "medium":
            warning = "The transcript is usable, but the summary may miss details."
            suggestions = ["Review the transcript before approving generated tasks."]

        return {
            "level": level,
            "score": score,
            "word_count": word_count,
            "unique_word_ratio": unique_word_ratio,
            "warning": warning,
            "suggestions": suggestions,
        }

    def extract_decisions(self, transcript: str) -> list[str]:
        return [self._legacy_decision_text(item) for item in self.extract_decision_items(transcript)]

    def extract_decision_items(self, transcript: str) -> list[dict[str, Any]]:
        decisions: list[dict[str, Any]] = []
        search_text = self._remove_task_sections(self._normalize_text(transcript))

        for sentence in self._sentences(search_text):
            lower_sentence = sentence.lower()
            if any(
                marker in lower_sentence
                for marker in ["decided", "agreed", "approved", "تم الاتفاق", "تم اعتماد", "قرر"]
            ):
                decisions.append(
                    {
                        "title": self._compact_title(sentence),
                        "description": sentence,
                        "confidence": None,
                    },
                )

        return decisions[:10]

    def extract_tasks(self, transcript: str) -> list[str]:
        return [item["title"] for item in self.extract_task_items(transcript)]

    def extract_task_items(self, transcript: str) -> list[dict[str, Any]]:
        clean_transcript = self._normalize_text(transcript)
        section_tasks = self._extract_task_items_from_sections(clean_transcript)
        if section_tasks:
            return section_tasks[:40]

        tasks: list[str] = []
        for sentence in self._sentences(clean_transcript):
            lower_sentence = sentence.lower()
            if any(
                marker in lower_sentence
                for marker in ["todo", "task", "tasks", "action item", "follow up", "will", "مهمة", "مهام", "تطوير", "إنشاء", "حفظ"]
            ) and self._is_actionable_task(sentence):
                tasks.append(sentence)

        priority = self._extract_priority(clean_transcript)
        return [
            {
                "title": self._compact_title(task),
                "description": task,
                "category": None,
                "priority": priority,
                "assignee": self._extract_assignee(task),
                "status": "pending",
            }
            for task in dedupe_keep_order(tasks)[:20]
        ]

    def _sentences(self, text: str) -> list[str]:
        normalized = " ".join(str(text or "").split())
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?؟])\s+", normalized)
            if sentence.strip()
        ]

    def _build_overview(
        self,
        sentences: list[str],
        decision_items: list[dict[str, Any]],
        task_items: list[dict[str, Any]],
    ) -> str:
        overview_parts = sentences[:4]
        if task_items:
            categories = sorted({str(item.get("category")) for item in task_items if item.get("category")})
            if categories:
                overview_parts.append(f"Detected task categories: {', '.join(categories)}.")
            else:
                overview_parts.append(f"Detected {len(task_items)} actionable task(s).")
        if decision_items:
            overview_parts.append(f"Detected {len(decision_items)} decision(s).")
        return " ".join(overview_parts)[:1200]

    def _repeated_phrase_count(self, text: str) -> int:
        words = re.findall(r"[\w\u0600-\u06ff]+", text or "", flags=re.UNICODE)
        if len(words) < 8:
            return 0
        phrases = [" ".join(words[index : index + 4]).casefold() for index in range(len(words) - 3)]
        seen: set[str] = set()
        repeated: set[str] = set()
        for phrase in phrases:
            if phrase in seen:
                repeated.add(phrase)
            seen.add(phrase)
        return len(repeated)

    def _analyze_with_groq(self, transcript: str) -> dict[str, Any]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You extract meeting intelligence for a project-management backend. "
                    "Return only JSON with keys: structured_summary, decision_items, task_items. "
                    "structured_summary must include title, overview, priority, key_points. "
                    "decision_items must be objects with title, description, confidence. "
                    "task_items must be objects with title, description, category, priority, assignee, status. "
                    "Extract every actionable task from Arabic or English sections named Tasks, المهام, Backend, Frontend, Database, or Testing. "
                    "Do not convert database table names into decisions unless the transcript says they were decided or approved. "
                    "Use only the transcript."
                ),
            },
            {
                "role": "user",
                "content": transcript[:24000],
            },
        ]

        try:
            result = self.llm_client.complete_json(messages)
        except HTTPException:
            raise

        decision_items = [self._normalize_decision_item(item) for item in result.get("decision_items") or result.get("decisions") or []]
        task_items = [self._normalize_task_item(item, transcript) for item in result.get("task_items") or result.get("tasks") or []]
        structured_summary = result.get("structured_summary")
        if not isinstance(structured_summary, dict):
            structured_summary = self.build_structured_summary(transcript, decision_items, task_items)

        return {
            "summary": self.summary_text(structured_summary),
            "structured_summary": structured_summary,
            "decisions": [self._legacy_decision_text(item) for item in decision_items][:10],
            "decision_items": decision_items[:10],
            "tasks": [item["title"] for item in task_items][:40],
            "task_items": task_items[:40],
        }

    def _extract_tasks_from_sections(self, transcript: str) -> list[str]:
        return [item["title"] for item in self._extract_task_items_from_sections(transcript)]

    def _extract_task_items_from_sections(self, transcript: str) -> list[dict[str, Any]]:
        text = " ".join(str(transcript or "").split())
        if not text:
            return []

        task_section_pattern = r"(?:المهام\s*\(Tasks\)|(?<!\()Tasks(?!\)))"
        section_matches = list(re.finditer(task_section_pattern, text, flags=re.IGNORECASE))
        if not section_matches:
            return []

        section = text[section_matches[-1].end() :]
        stop_match = re.search(
            r"(?:السيناريوهات|Scenarios|Decisions|القرارات|Knowledge chunks)\s*(?:\([^)]*\))?",
            section,
            flags=re.IGNORECASE,
        )
        if stop_match:
            section = section[: stop_match.start()]

        categories = list(
            re.finditer(
                r"(?:مهام|Tasks)?\s*"
                r"(?P<label>الواجهة الخلفية|الواجهة الأمامية|قاعدة البيانات|الاختبار|Backend|Frontend|Database|Testing)"
                r"\s*(?:\((?P<en>Backend|Frontend|Database|Testing)\))?",
                section,
                flags=re.IGNORECASE,
            ),
        )
        priority = self._extract_priority(text)

        if not categories:
            return self._task_items_from_bullets(section, None, priority)

        tasks: list[dict[str, Any]] = []
        for index, match in enumerate(categories):
            start = match.end()
            end = categories[index + 1].start() if index + 1 < len(categories) else len(section)
            category = self._normalize_category(match.group("en") or match.group("label"))
            tasks.extend(self._task_items_from_bullets(section[start:end], category, priority))

        return dedupe_task_items(tasks)

    def _task_items_from_bullets(self, section: str, category: str | None, priority: str | None) -> list[dict[str, Any]]:
        raw_items = re.split(r"(?:●|•|○|\n\s*[-*]\s+|\s-\s)", section)
        tasks = []
        for item in raw_items:
            clean_item = self._clean_task_item(item)
            if not clean_item:
                continue
            tasks.append(
                {
                    "title": self._compact_title(clean_item),
                    "description": clean_item,
                    "category": category,
                    "priority": priority,
                    "assignee": self._extract_assignee(clean_item),
                    "status": "pending",
                },
            )
        return tasks

    def _clean_task_item(self, value: str) -> str:
        item = re.sub(r"\s+", " ", value).strip(" .:-،")
        if len(item) < 8:
            return ""
        heading = re.sub(r"[\s().،:]+", "", item).casefold()
        if heading in {"backend", "frontend", "database", "testing", "المهام", "tasks"}:
            return ""
        if not self._is_actionable_task(item):
            return ""
        return item[:500]

    def _normalize_text(self, text: str) -> str:
        value = str(text or "").replace("\u200f", " ").replace("\u200e", " ")
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()

    def _remove_task_sections(self, text: str) -> str:
        return re.split(r"(?:المهام\s*\(Tasks\)|(?<!\()Tasks(?!\)))", text, flags=re.IGNORECASE)[0]

    def _extract_title(self, text: str) -> str | None:
        match = re.search(r"(?:اسم قصة المستخدم|User Story)\s*(?:\([^)]*\))?\s*([^.\n]{12,120})", text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" :-")
        sentences = self._sentences(text)
        return self._compact_title(sentences[0]) if sentences else None

    def _extract_priority(self, text: str) -> str | None:
        if re.search(r"(?:عالية|High|Must Have)", text, flags=re.IGNORECASE):
            return "High"
        if re.search(r"(?:متوسطة|Medium)", text, flags=re.IGNORECASE):
            return "Medium"
        if re.search(r"(?:منخفضة|Low)", text, flags=re.IGNORECASE):
            return "Low"
        return None

    def _extract_assignee(self, text: str) -> str | None:
        match = re.search(r"(?:assigned to|owner|المسؤول|الشخص المقترح)\s*[:：]?\s*([^،.]+)", text, flags=re.IGNORECASE)
        return match.group(1).strip()[:255] if match else None

    def _compact_title(self, text: str) -> str:
        title = re.sub(r"\s+", " ", str(text or "")).strip(" .:-،")
        return title[:120]

    def _legacy_decision_text(self, item: dict[str, Any]) -> str:
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()
        title_key = title.strip(" .:-،").casefold()
        description_key = description.strip(" .:-،").casefold()
        if title and description and title_key != description_key:
            return f"{title}: {description}"
        return description or title

    def _normalize_category(self, value: str | None) -> str | None:
        if not value:
            return None
        normalized = re.sub(r"\s+", " ", value).strip().casefold()
        if "backend" in normalized or "الخلفية" in normalized:
            return "Backend"
        if "frontend" in normalized or "الأمامية" in normalized:
            return "Frontend"
        if "database" in normalized or "قاعدة" in normalized:
            return "Database"
        if "testing" in normalized or "اختبار" in normalized:
            return "Testing"
        return value.strip()

    def _normalize_decision_item(self, item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            description = str(item.get("description") or item.get("decision_text") or item.get("title") or "").strip()
            title = str(item.get("title") or self._compact_title(description)).strip()
            confidence = item.get("confidence")
        else:
            description = str(item).strip()
            title = self._compact_title(description)
            confidence = None
        return {"title": title, "description": description, "confidence": confidence}

    def _normalize_task_item(self, item: Any, transcript: str) -> dict[str, Any]:
        if isinstance(item, dict):
            description = str(item.get("description") or item.get("task_text") or item.get("title") or "").strip()
            title = str(item.get("title") or self._compact_title(description)).strip()
            category = self._normalize_category(item.get("category"))
            priority = item.get("priority") or self._extract_priority(transcript)
            assignee = item.get("assignee") or self._extract_assignee(description)
            status = item.get("status") or "pending"
        else:
            description = str(item).strip()
            title = self._compact_title(description)
            category = None
            priority = self._extract_priority(transcript)
            assignee = self._extract_assignee(description)
            status = "pending"
        if not self._is_actionable_task(description or title):
            return {}
        return {
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "assignee": assignee,
            "status": status,
        }

    def _normalize_result(self, result: dict[str, Any]) -> dict[str, Any]:
        decision_items = [self._normalize_decision_item(item) for item in result.get("decision_items") or []]
        task_items = [
            item
            for item in (self._normalize_task_item(item, "") for item in result.get("task_items") or [])
            if item
        ]
        structured_summary = result.get("structured_summary") if isinstance(result.get("structured_summary"), dict) else {}
        return {
            "summary": str(result.get("summary") or self.summary_text(structured_summary)),
            "structured_summary": structured_summary,
            "transcript_quality": result.get("transcript_quality") or self.assess_transcript_quality(""),
            "decisions": [
                str(item)
                for item in result.get("decisions") or [self._legacy_decision_text(item) for item in decision_items]
                if str(item).strip()
            ],
            "decision_items": decision_items,
            "tasks": [
                str(item)
                for item in result.get("tasks") or [item["title"] for item in task_items]
                if str(item).strip() and self._is_actionable_task(str(item))
            ],
            "task_items": task_items,
        }

    def _is_actionable_task(self, text: str) -> bool:
        value = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(value) < 12:
            return False

        words = re.findall(r"[\w\u0600-\u06ff]+", value, flags=re.UNICODE)
        if len(words) < 3:
            return False

        lower_value = value.casefold()
        if self._looks_like_media_noise(lower_value):
            return False

        arabic_action_markers = [
            "إنشاء",
            "تطوير",
            "تنفيذ",
            "مراجعة",
            "تحديث",
            "إضافة",
            "ربط",
            "رفع",
            "حفظ",
            "اختبار",
            "إصلاح",
            "إعداد",
            "تجهيز",
            "توثيق",
            "تحسين",
            "عرض",
            "متابعة",
            "سيقوم",
            "سوف",
            "يجب",
            "لازم",
            "المطلوب",
        ]
        english_action_markers = [
            " will ",
            " should ",
            " must ",
            " need to ",
            " needs to ",
            "todo",
            "task",
            "action item",
            "follow up",
            "create",
            "build",
            "implement",
            "review",
            "update",
            "fix",
            "test",
            "prepare",
            "connect",
            "upload",
            "document",
        ]

        padded = f" {lower_value} "
        return any(marker.casefold() in lower_value for marker in arabic_action_markers) or any(
            marker in padded for marker in english_action_markers
        )

    def _looks_like_media_noise(self, lower_value: str) -> bool:
        noise_markers = [
            "click on the bell",
            "subscribe",
            "like and subscribe",
            "watch the bell",
            "post the bell",
            "for more information",
            "remove the link",
            "show you later",
            "background music",
            "ignore subtitles",
            "subtitles background",
            "at the same time at the same time",
            "basic language",
            "public services",
            "persons with disabilities",
            "government department",
        ]
        return any(marker in lower_value for marker in noise_markers)


def dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def dedupe_task_items(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for value in values:
        key = str(value.get("title") or value.get("description") or "").casefold()
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result
