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
        job_description: str | None = None,
    ) -> dict[str, Any]:
        document_type = self.detect_document_type(
            transcript,
            source_type=source_type,
            meeting_analysis=meeting_analysis,
        )

        if document_type == "cv":
            structured_result = self._analyze_cv(transcript, job_description=job_description)
            summary = self._cv_summary(structured_result)
        elif document_type == "contract":
            structured_result = self._analyze_contract(transcript)
            summary = structured_result["executive_summary"]
        elif document_type == "invoice":
            structured_result = self._analyze_invoice(transcript)
            summary = structured_result["overview"]
        elif document_type == "proposal":
            structured_result = self._analyze_proposal(transcript)
            summary = structured_result["overview"]
        elif document_type == "company_policy":
            structured_result = self._analyze_company_policy(transcript)
            summary = structured_result["overview"]
        elif document_type == "report":
            structured_result = self._analyze_report(transcript)
            summary = structured_result["overview"]
        elif document_type == "legal_document":
            structured_result = self._analyze_legal_document(transcript)
            summary = structured_result["overview"]
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
        if self._looks_like_contract(text):
            return "contract"
        if self._looks_like_invoice(text):
            return "invoice"
        if self._looks_like_proposal(text):
            return "proposal"
        if self._looks_like_company_policy(text):
            return "company_policy"
        if self._looks_like_report(text):
            return "report"
        if self._looks_like_legal_document(text):
            return "legal_document"
        if meeting_analysis.get("decision_items") or meeting_analysis.get("task_items"):
            return "meeting"
        if any(marker in text for marker in ("meeting", "agenda", "minutes", "action item", "decided", "agreed")):
            return "meeting"
        return "document"

    def _analyze_cv(self, transcript: str, *, job_description: str | None = None) -> dict[str, Any]:
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

        job_match = self._cv_job_match(skills, transcript, job_description)
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
            "job_match": job_match,
            "recommendations": self._cv_recommendations(transcript, job_match),
        }

    def _analyze_contract(self, transcript: str) -> dict[str, Any]:
        parties = self._contract_parties(transcript)
        start_date = self._first_labeled_value(
            transcript,
            ["start date", "effective date", "commencement date", "تاريخ البدء", "تاريخ السريان"],
        )
        end_date = self._first_labeled_value(
            transcript,
            ["end date", "expiry date", "expiration date", "termination date", "تاريخ الانتهاء", "تاريخ نهاية"],
        )
        payments = self._extract_payment_terms(transcript)
        obligations = self._extract_lines_near_keywords(
            self._meaningful_lines(transcript),
            ["obligation", "shall", "must", "responsible", "يلتزم", "واجب", "مسؤول"],
        )
        termination_terms = self._extract_lines_near_keywords(
            self._meaningful_lines(transcript),
            ["termination", "terminate", "cancel", "cancellation", "إنهاء", "فسخ", "إلغاء"],
        )
        risks = self._contract_risks(transcript, parties, start_date, end_date, payments, termination_terms)

        return {
            "executive_summary": self._contract_summary(parties, start_date, end_date, payments, risks),
            "parties": parties,
            "start_date": start_date,
            "end_date": end_date,
            "obligations": obligations[:12],
            "payments": payments,
            "termination_terms": termination_terms[:8],
            "sla_terms": self._extract_lines_near_keywords(
                self._meaningful_lines(transcript),
                ["sla", "service level", "response time", "uptime", "critical bugs", "within", "مستوى الخدمة"],
            )[:8],
            "penalties": self._extract_lines_near_keywords(
                self._meaningful_lines(transcript),
                ["penalty", "penalties", "late fee", "liquidated damages", "غرامة", "جزاء"],
            )[:8],
            "renewal_terms": self._extract_lines_near_keywords(
                self._meaningful_lines(transcript),
                ["renewal", "renew", "auto-renew", "automatic renewal", "تجديد"],
            )[:8],
            "risks": risks,
            "legal_risk_score": self._legal_risk_score(risks),
            "missing_clauses": self._contract_missing_clauses(transcript),
            "clause_review": self._contract_clause_review(transcript),
            "key_points": self._key_points(transcript),
        }

    def _analyze_invoice(self, transcript: str) -> dict[str, Any]:
        return {
            "overview": self._overview(transcript),
            "invoice_number": self._first_labeled_value(transcript, ["invoice number", "invoice no", "رقم الفاتورة"]),
            "total_amounts": self._money_amounts(transcript),
            "dates": self._dates(transcript),
            "vendor_or_customer": self._first_labeled_value(transcript, ["vendor", "customer", "bill to", "from"]),
            "line_preview": self._meaningful_lines(transcript)[:12],
        }

    def _analyze_proposal(self, transcript: str) -> dict[str, Any]:
        return {
            "overview": self._overview(transcript),
            "objectives": self._extract_lines_near_keywords(self._meaningful_lines(transcript), ["objective", "goal", "هدف"]),
            "scope": self._extract_lines_near_keywords(self._meaningful_lines(transcript), ["scope", "deliverable", "نطاق", "مخرجات"]),
            "pricing": self._money_amounts(transcript),
            "timeline": self._extract_lines_near_keywords(self._meaningful_lines(transcript), ["timeline", "deadline", "schedule", "موعد"]),
            "risks": [],
        }

    def _analyze_company_policy(self, transcript: str) -> dict[str, Any]:
        return {
            "overview": self._overview(transcript),
            "policy_title": self._document_title(transcript),
            "rules": self._extract_lines_near_keywords(self._meaningful_lines(transcript), ["policy", "must", "required", "prohibited", "سياسة", "يجب", "ممنوع"]),
            "exceptions": self._extract_lines_near_keywords(self._meaningful_lines(transcript), ["exception", "unless", "استثناء"]),
            "topics": self._topics(transcript),
        }

    def _analyze_report(self, transcript: str) -> dict[str, Any]:
        return {
            "overview": self._overview(transcript),
            "title": self._document_title(transcript),
            "findings": self._extract_lines_near_keywords(self._meaningful_lines(transcript), ["finding", "result", "analysis", "نتيجة", "تحليل"]),
            "recommendations": self._extract_lines_near_keywords(self._meaningful_lines(transcript), ["recommend", "recommendation", "suggest", "توصية", "نقترح"]),
            "topics": self._topics(transcript),
        }

    def _analyze_legal_document(self, transcript: str) -> dict[str, Any]:
        return {
            "overview": self._overview(transcript),
            "title": self._document_title(transcript),
            "legal_terms": self._extract_lines_near_keywords(self._meaningful_lines(transcript), ["liability", "confidential", "jurisdiction", "warranty", "مسؤولية", "سرية", "اختصاص"]),
            "risks": self._generic_legal_risks(transcript),
            "key_points": self._key_points(transcript),
        }

    def _analyze_meeting(self, meeting_analysis: dict[str, Any]) -> dict[str, Any]:
        return {
            "overview": str(meeting_analysis.get("summary") or ""),
            "structured_summary": meeting_analysis.get("structured_summary"),
            "decisions": meeting_analysis.get("decision_items") or [],
            "tasks": meeting_analysis.get("task_items") or [],
        }

    def _analyze_media(self, transcript: str, meeting_analysis: dict[str, Any]) -> dict[str, Any]:
        speaker_segments = self._speaker_segments(transcript)
        return {
            "overview": self._overview(transcript),
            "transcript_word_count": len(self._words(transcript)),
            "topics": self._topics(transcript),
            "speaker_diarization_status": "estimated_from_timestamped_chunks" if speaker_segments else "not_available",
            "speaker_segments": speaker_segments,
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

    def _looks_like_contract(self, text: str) -> bool:
        markers = [
            "contract",
            "agreement",
            "party",
            "parties",
            "effective date",
            "termination",
            "obligations",
            "payment terms",
            "whereas",
            "عقد",
            "اتفاقية",
            "الطرف الأول",
            "الطرف الثاني",
            "يلتزم",
            "فسخ",
        ]
        return sum(1 for marker in markers if marker in text) >= 2

    def _looks_like_invoice(self, text: str) -> bool:
        markers = ["invoice", "bill to", "amount due", "total", "tax", "فاتورة", "المبلغ المستحق", "ضريبة"]
        return sum(1 for marker in markers if marker in text) >= 2

    def _looks_like_proposal(self, text: str) -> bool:
        markers = ["proposal", "scope of work", "deliverables", "pricing", "timeline", "عرض سعر", "مقترح", "نطاق العمل"]
        return sum(1 for marker in markers if marker in text) >= 2

    def _looks_like_company_policy(self, text: str) -> bool:
        markers = ["policy", "procedure", "employee handbook", "code of conduct", "سياسة", "إجراء", "مدونة السلوك"]
        return sum(1 for marker in markers if marker in text) >= 2

    def _looks_like_report(self, text: str) -> bool:
        markers = ["report", "executive summary", "findings", "analysis", "recommendations", "تقرير", "ملخص تنفيذي", "نتائج"]
        return sum(1 for marker in markers if marker in text) >= 2

    def _looks_like_legal_document(self, text: str) -> bool:
        markers = ["legal", "liability", "jurisdiction", "confidentiality", "warranty", "قانوني", "مسؤولية", "اختصاص", "سرية"]
        return sum(1 for marker in markers if marker in text) >= 2

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

    def _cv_job_match(
        self,
        skills: list[str],
        transcript: str,
        job_description: str | None,
    ) -> dict[str, Any] | None:
        if not job_description:
            return None

        required_terms = self._topics(job_description)[:20]
        transcript_text = transcript.casefold()
        matched = [term for term in required_terms if term.casefold() in transcript_text]
        missing = [term for term in required_terms if term not in matched][:10]
        skill_matches = [skill for skill in skills if skill.casefold() in job_description.casefold()]
        score = round((len(matched) / max(len(required_terms), 1)) * 70 + min(len(skill_matches), 10) * 3)

        return {
            "score": max(0, min(score, 100)),
            "matched_terms": matched[:10],
            "missing_terms": missing,
            "matched_skills": skill_matches,
        }

    def _cv_recommendations(self, transcript: str, job_match: dict[str, Any] | None) -> list[str]:
        recommendations = []
        if not re.search(r"\blinkedin\b", transcript, flags=re.IGNORECASE):
            recommendations.append("Add a LinkedIn profile link.")
        if not re.search(r"\bgithub\b", transcript, flags=re.IGNORECASE):
            recommendations.append("Add a GitHub profile link.")
        if not re.search(r"\bportfolio\b", transcript, flags=re.IGNORECASE):
            recommendations.append("Add a portfolio link or project demo.")
        if job_match and job_match.get("missing_terms"):
            recommendations.append("Add evidence for missing job requirements where accurate.")
        return recommendations

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

    def _first_labeled_value(self, text: str, labels: list[str]) -> str | None:
        for label in labels:
            pattern = rf"{re.escape(label)}\s*[:\-]\s*([^\n.;]{{2,120}})"
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _contract_parties(self, text: str) -> list[str]:
        parties = []
        for label in ["party a", "party b", "first party", "second party", "client", "provider", "الطرف الأول", "الطرف الثاني"]:
            value = self._first_labeled_value(text, [label])
            if value:
                parties.append(value)
        if parties:
            return list(dict.fromkeys(parties))[:6]
        return self._extract_lines_near_keywords(self._meaningful_lines(text), ["party", "between", "الطرف"])[:4]

    def _extract_payment_terms(self, text: str) -> list[str]:
        lines = self._extract_lines_near_keywords(
            self._meaningful_lines(text),
            ["payment", "fee", "amount", "invoice", "installment", "دفعة", "مبلغ", "رسوم", "فاتورة"],
        )
        amounts = self._money_amounts(text)
        return list(dict.fromkeys([*lines[:8], *amounts[:8]]))

    def _money_amounts(self, text: str) -> list[str]:
        pattern = r"(?:[$€£]\s?\d[\d,]*(?:\.\d{1,2})?|\d[\d,]*(?:\.\d{1,2})?\s?(?:USD|EUR|GBP|NIS|ILS|SAR|AED|دولار|شيكل|ريال|درهم))"
        return list(dict.fromkeys(match.group(0).strip() for match in re.finditer(pattern, text, flags=re.IGNORECASE)))[:12]

    def _dates(self, text: str) -> list[str]:
        pattern = r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b"
        return list(dict.fromkeys(match.group(0).strip() for match in re.finditer(pattern, text, flags=re.IGNORECASE)))[:12]

    def _contract_risks(
        self,
        text: str,
        parties: list[str],
        start_date: str | None,
        end_date: str | None,
        payments: list[str],
        termination_terms: list[str],
    ) -> list[str]:
        risks = []
        if not parties:
            risks.append("Contract parties are not clearly identified.")
        if not start_date:
            risks.append("Start or effective date is not clearly identified.")
        if not end_date:
            risks.append("End, expiry, or termination date is not clearly identified.")
        if not payments:
            risks.append("Payment amounts or payment terms are not clearly identified.")
        if not termination_terms:
            risks.append("Termination or cancellation terms are not clearly identified.")
        risks.extend(self._generic_legal_risks(text))
        return list(dict.fromkeys(risks))[:12]

    def _contract_missing_clauses(self, text: str) -> list[str]:
        required = {
            "confidentiality": ["confidentiality", "سرية"],
            "liability": ["liability", "مسؤولية"],
            "termination": ["termination", "terminate", "فسخ", "إنهاء"],
            "payment terms": ["payment", "fee", "دفعة", "مبلغ"],
            "governing law": ["governing law", "jurisdiction", "القانون", "اختصاص"],
        }
        lower_text = text.casefold()
        return [label for label, markers in required.items() if not any(marker in lower_text for marker in markers)]

    def _contract_summary(
        self,
        parties: list[str],
        start_date: str | None,
        end_date: str | None,
        payments: list[str],
        risks: list[str],
    ) -> str:
        party_text = ", ".join(parties) if parties else "parties not clearly extracted"
        date_text = f"Start: {start_date or 'not clear'}; End: {end_date or 'not clear'}"
        payment_text = "; ".join(payments[:3]) if payments else "payment terms not clear"
        risk_text = f"{len(risks)} review item(s)" if risks else "no major rule-based risks detected"
        return f"Contract between {party_text}. {date_text}. Payments: {payment_text}. Legal review: {risk_text}."

    def _generic_legal_risks(self, text: str) -> list[str]:
        risks = []
        if re.search(r"\b(unlimited liability|sole discretion|without notice|non-refundable)\b", text, flags=re.IGNORECASE):
            risks.append("Potentially strict legal wording detected; review liability, discretion, notice, or refund terms.")
        if re.search(r"\b(auto(?:matic)? renewal|renew automatically)\b", text, flags=re.IGNORECASE):
            risks.append("Automatic renewal wording detected; confirm notice period and cancellation process.")
        return risks

    def _legal_risk_score(self, risks: list[str]) -> int:
        return min(100, len(risks) * 20)

    def _contract_clause_review(self, text: str) -> list[dict[str, Any]]:
        clauses = {
            "parties": ["party a", "party b", "الطرف الأول", "الطرف الثاني"],
            "scope": ["scope", "statement of work", "نطاق"],
            "payments": ["payment", "fee", "invoice", "دفعة", "مبلغ"],
            "confidentiality": ["confidentiality", "سرية"],
            "termination": ["termination", "terminate", "فسخ", "إنهاء"],
            "liability": ["liability", "مسؤولية"],
            "governing_law": ["governing law", "jurisdiction", "القانون", "اختصاص"],
            "renewal": ["renewal", "renew", "تجديد"],
            "penalties": ["penalty", "penalties", "غرامة", "جزاء"],
            "sla": ["sla", "service level", "response time", "uptime", "مستوى الخدمة"],
        }
        lower_text = text.casefold()
        return [
            {
                "clause": clause,
                "status": "present" if any(marker in lower_text for marker in markers) else "missing",
            }
            for clause, markers in clauses.items()
        ]

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

    def _speaker_segments(self, transcript: str) -> list[dict[str, Any]]:
        pattern = re.compile(
            r"\[(?P<start>\d{2}:\d{2}:\d{2})-(?P<end>\d{2}:\d{2}:\d{2})\]\s*(?P<text>.*?)(?=\s*\[\d{2}:\d{2}:\d{2}-\d{2}:\d{2}:\d{2}\]|\Z)",
            flags=re.DOTALL,
        )
        segments = []
        for index, match in enumerate(pattern.finditer(transcript)):
            text = " ".join(match.group("text").split()).strip()
            if not text:
                continue
            speaker = self._speaker_label(text) or f"Speaker {index + 1}"
            segments.append(
                {
                    "speaker": speaker,
                    "start": match.group("start"),
                    "end": match.group("end"),
                    "text": text,
                }
            )
        return segments

    def _speaker_label(self, text: str) -> str | None:
        match = re.match(r"(?:speaker|المتحدث)\s*(\d+|[A-Za-z]+)\s*[:：-]", text, flags=re.IGNORECASE)
        if match:
            return f"Speaker {match.group(1)}"
        return None

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
