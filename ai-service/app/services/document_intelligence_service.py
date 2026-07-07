"""Document type detection and structured analysis helpers."""

from __future__ import annotations

import re
from typing import Any


class DocumentIntelligenceService:
    def analyze(
        self,
        transcript: str,
        *,
        source_type: str,
        meeting_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        document_type = self.detect_document_type(
            transcript,
            source_type=source_type,
            meeting_analysis=meeting_analysis,
        )

        if document_type == "cv":
            structured_result = self._analyze_cv(transcript)
            summary = self._cv_summary(structured_result)
        elif document_type == "meeting":
            structured_result = self._analyze_meeting(meeting_analysis)
            summary = str(meeting_analysis.get("summary") or "")
        elif document_type == "media":
            structured_result = self._analyze_media(transcript, meeting_analysis)
            summary = str(meeting_analysis.get("summary") or structured_result["overview"])
        elif document_type == "spreadsheet":
            structured_result = self._analyze_spreadsheet(transcript)
            summary = structured_result["overview"]
        else:
            structured_result = self._analyze_document(transcript)
            summary = structured_result["overview"]

        warnings = self._warnings(transcript, meeting_analysis)

        return {
            "document_type": document_type,
            "summary": summary,
            "structured_result": structured_result,
            "quality": {
                "extraction": self._extraction_quality(transcript, meeting_analysis),
                "analysis": self._analysis_quality(meeting_analysis),
                "requires_review": bool(warnings),
            },
            "warnings": warnings,
        }

    def detect_document_type(
        self,
        transcript: str,
        *,
        source_type: str,
        meeting_analysis: dict[str, Any],
    ) -> str:
        text = transcript.casefold()
        if source_type == "media":
            return "media"
        if source_type == "xlsx":
            return "spreadsheet"
        if self._looks_like_cv(text):
            return "cv"
        if meeting_analysis.get("decision_items") or meeting_analysis.get("task_items"):
            return "meeting"
        if any(marker in text for marker in ("meeting", "agenda", "minutes", "action item", "decided", "agreed")):
            return "meeting"
        return "document"

    def _analyze_cv(self, transcript: str) -> dict[str, Any]:
        lines = self._meaningful_lines(transcript)
        skills = self._extract_known_terms(
            transcript,
            [
                "PHP",
                "Laravel",
                "REST API",
                "RESTful APIs",
                "MySQL",
                "Database Design",
                "Flutter",
                "Dart",
                "Python",
                "C++",
                "Java",
                "Git",
                "GitHub",
                "Linux",
                "Postman",
                "DevOps",
            ],
        )

        return {
            "candidate_name": self._extract_candidate_name(lines),
            "title": self._extract_cv_title(lines),
            "contact": {
                "email": self._first_match(r"[\w.+-]+@[\w.-]+\.\w+", transcript),
                "phone": self._first_match(r"\+?\d[\d\s().-]{7,}\d", transcript),
                "website": self._first_match(r"\b(?:https?://)?[a-z0-9-]+\.[a-z]{2,}(?:\.[a-z]{2,})?\b", transcript),
            },
            "skills": skills,
            "education": self._extract_lines_near_keywords(lines, ["education", "degree", "university", "student"]),
            "experience": self._extract_lines_near_keywords(lines, ["experience", "developer", "engineer"]),
            "projects": self._extract_lines_near_keywords(lines, ["project", "application", "api", "app"]),
            "languages": self._extract_known_terms(transcript, ["Arabic", "English"]),
            "achievements": self._extract_lines_near_keywords(lines, ["place", "contest", "competition", "achievement"]),
            "strengths": self._cv_strengths(skills, transcript),
            "weaknesses": self._cv_gaps(transcript),
            "score": self._cv_score(skills, transcript),
        }

    def _analyze_meeting(self, meeting_analysis: dict[str, Any]) -> dict[str, Any]:
        return {
            "overview": str(meeting_analysis.get("summary") or ""),
            "structured_summary": meeting_analysis.get("structured_summary"),
            "decisions": meeting_analysis.get("decision_items") or [],
            "tasks": meeting_analysis.get("task_items") or [],
        }

    def _analyze_media(self, transcript: str, meeting_analysis: dict[str, Any]) -> dict[str, Any]:
        return {
            "overview": self._overview(transcript),
            "transcript_word_count": len(self._words(transcript)),
            "topics": self._topics(transcript),
            "decisions": meeting_analysis.get("decision_items") or [],
            "tasks": meeting_analysis.get("task_items") or [],
        }

    def _analyze_spreadsheet(self, transcript: str) -> dict[str, Any]:
        lines = self._meaningful_lines(transcript)
        sheets = [line.removeprefix("Sheet:").strip() for line in lines if line.startswith("Sheet:")]
        return {
            "overview": self._overview(transcript),
            "sheets": sheets,
            "row_preview": [line for line in lines if not line.startswith("Sheet:")][:10],
            "topics": self._topics(transcript),
        }

    def _analyze_document(self, transcript: str) -> dict[str, Any]:
        return {
            "title": self._document_title(transcript),
            "overview": self._overview(transcript),
            "key_points": self._key_points(transcript),
            "topics": self._topics(transcript),
            "recommendations": [],
            "risks": [],
        }

    def _warnings(self, transcript: str, meeting_analysis: dict[str, Any]) -> list[str]:
        warnings: list[str] = []
        quality = meeting_analysis.get("transcript_quality") or {}
        if quality.get("level") in {"low", "medium"} and quality.get("warning"):
            warnings.append(str(quality["warning"]))
        if re.search(r"\b[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\b", transcript):
            warnings.append("Extracted text may still contain spaced PDF glyph artifacts.")
        if len(self._words(transcript)) < 20:
            warnings.append("Extracted text is too short for reliable analysis.")
        return list(dict.fromkeys(warnings))

    def _extraction_quality(self, transcript: str, meeting_analysis: dict[str, Any]) -> str:
        quality = meeting_analysis.get("transcript_quality") or {}
        return str(quality.get("level") or "medium")

    def _analysis_quality(self, meeting_analysis: dict[str, Any]) -> str:
        quality = meeting_analysis.get("transcript_quality") or {}
        if quality.get("level") == "low":
            return "low"
        if quality.get("level") == "medium":
            return "medium"
        return "high"

    def _looks_like_cv(self, text: str) -> bool:
        markers = [
            "curriculum vitae",
            "resume",
            "education",
            "skills",
            "technical skills",
            "experience",
            "projects",
            "languages",
            "achievements",
            "career objective",
            "software engineer",
            "developer",
        ]
        return sum(1 for marker in markers if marker in text) >= 3

    def _cv_summary(self, result: dict[str, Any]) -> str:
        name = result.get("candidate_name") or "Candidate"
        title = result.get("title") or "professional profile"
        skills = ", ".join(result.get("skills") or []) or "skills not clearly extracted"
        score = result.get("score")
        return f"{name} is presented as a {title}. Key skills: {skills}. CV readiness score: {score}/100."

    def _cv_strengths(self, skills: list[str], transcript: str) -> list[str]:
        strengths = []
        if len(skills) >= 5:
            strengths.append("Broad technical skill set")
        if re.search(r"\b(api|backend|laravel|database)\b", transcript, flags=re.IGNORECASE):
            strengths.append("Backend/API experience")
        if re.search(r"\b(contest|competition|place)\b", transcript, flags=re.IGNORECASE):
            strengths.append("Competitive programming achievements")
        return strengths

    def _cv_gaps(self, transcript: str) -> list[str]:
        gaps = []
        if not re.search(r"\bexperience\b", transcript, flags=re.IGNORECASE):
            gaps.append("Professional experience section is not clearly labeled")
        if not re.search(r"\bgithub|portfolio|linkedin\b", transcript, flags=re.IGNORECASE):
            gaps.append("Portfolio or social links are limited")
        return gaps

    def _cv_score(self, skills: list[str], transcript: str) -> int:
        score = 45
        score += min(len(skills), 10) * 3
        for marker in ("education", "projects", "email", "@", "experience", "achievement"):
            if marker in transcript.casefold():
                score += 5
        return max(0, min(score, 100))

    def _extract_candidate_name(self, lines: list[str]) -> str | None:
        for line in lines[:20]:
            if re.fullmatch(r"[A-Z][A-Za-z .'-]{1,60}", line) and not self._is_cv_section(line):
                return line
        initials = next((line for line in lines[:20] if re.fullmatch(r"[A-Z]{1,4}", line)), None)
        return initials

    def _extract_cv_title(self, lines: list[str]) -> str | None:
        for line in lines[:30]:
            if re.search(r"\b(engineer|developer|student|designer|manager)\b", line, flags=re.IGNORECASE):
                return line[:120]
        return None

    def _extract_lines_near_keywords(self, lines: list[str], keywords: list[str]) -> list[str]:
        matches = []
        for line in lines:
            lower = line.casefold()
            if any(keyword in lower for keyword in keywords):
                matches.append(line)
        return matches[:12]

    def _extract_known_terms(self, text: str, terms: list[str]) -> list[str]:
        found = []
        for term in terms:
            pattern = re.escape(term).replace(r"\ ", r"\s+")
            if re.search(rf"(?<!\w){pattern}(?!\w)", text, flags=re.IGNORECASE):
                found.append(term)
        return found

    def _first_match(self, pattern: str, text: str) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(0).strip() if match else None

    def _document_title(self, transcript: str) -> str | None:
        lines = self._meaningful_lines(transcript)
        return lines[0][:120] if lines else None

    def _overview(self, transcript: str) -> str:
        sentences = self._sentences(transcript)
        if sentences:
            return " ".join(sentences[:4])[:1000]
        lines = self._meaningful_lines(transcript)
        return " ".join(lines[:6])[:1000]

    def _key_points(self, transcript: str) -> list[str]:
        return self._sentences(transcript)[:8]

    def _topics(self, transcript: str) -> list[str]:
        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "this",
            "that",
            "will",
            "have",
            "software",
            "system",
        }
        words = [
            word
            for word in self._words(transcript)
            if len(word) > 3 and word.casefold() not in stop_words
        ]
        counts: dict[str, int] = {}
        labels: dict[str, str] = {}
        for word in words:
            key = word.casefold()
            counts[key] = counts.get(key, 0) + 1
            labels.setdefault(key, word)
        ranked = sorted(counts, key=lambda key: (-counts[key], key))
        return [labels[key] for key in ranked[:10]]

    def _sentences(self, text: str) -> list[str]:
        normalized = " ".join(str(text or "").split())
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?؟])\s+", normalized)
            if sentence.strip()
        ]

    def _meaningful_lines(self, text: str) -> list[str]:
        return [line.strip() for line in str(text or "").splitlines() if line.strip()]

    def _words(self, text: str) -> list[str]:
        return re.findall(r"[\w\u0600-\u06ff+#.]+", text or "", flags=re.UNICODE)

    def _is_cv_section(self, line: str) -> bool:
        return line.casefold() in {
            "education",
            "technical skills",
            "skills",
            "projects",
            "featured projects",
            "languages",
            "interests",
            "achievements",
            "career objective",
        }
