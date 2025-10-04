import os
import re
import json
from typing import List
from presidio_analyzer import RecognizerResult, LocalRecognizer
from ahocorasick import Automaton


class LowThresholdHIPAARecognizer(LocalRecognizer):
    """Self-contained recognizer for HIPAA Low Threshold policy."""

    def __init__(self, supported_language="en"):
        super().__init__(
            supported_entities=["HIPAA_HITECH_LOW_THRESHOLD"],
            supported_language=supported_language,
        )

        self.NUMBER_PATTERN = re.compile(r"\b\d{6,}\b")
        self.SSN_PATTERN = re.compile(r"\b\d{9}\b")
        self.DATE_PATTERN = re.compile(
            r"\b(?:DOB|DOS|Date of Birth|Date of Service)[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})\b", re.IGNORECASE)
        self.NAME_PATTERN = re.compile(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b")

        self.automaton = Automaton()
        self._load_medical_terms()

    def _load_medical_terms(self):
        base_path = "/usr/share/data"

        def safe_load(path):
            with open(os.path.join(base_path, path)) as f:
                return json.load(f)

        try:
            # Load ICD-9 codes
            for item in safe_load("ValidICD9-Jan2024.json"):
                code = item.get("CODE")
                desc = item.get("LONG DESCRIPTION (VALID ICD-9 FY2024)", "")
                if code:
                    self.automaton.add_word(code.lower(), (code, "ICD9"))
                if desc:
                    self.automaton.add_word(desc.lower(), (desc, "ICD9_DESC"))

            # Load ICD-10 codes/descriptions
            for item in safe_load("ValidICD10-Jan2024.json"):
                code = item.get("CODE")
                for key in ["SHORT DESCRIPTION (VALID ICD-10 FY2024)", "LONG DESCRIPTION (VALID ICD-10 FY2024)"]:
                    if item.get(key):
                        self.automaton.add_word(item[key].lower(), (item[key], "ICD10_DESC"))
                if code:
                    self.automaton.add_word(code.lower(), (code, "ICD10"))

            # Load drugs
            for drug in safe_load("Drugs.json"):
                self.automaton.add_word(drug.lower(), (drug, "DRUG"))

            # Load ingredients
            for ing in safe_load("Ingredients.json"):
                self.automaton.add_word(ing.lower(), (ing, "INGREDIENT"))

            self.automaton.make_automaton()

        except Exception as e:
            print("Failed to load medical terms:", e)

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        if "HIPAA_HITECH_LOW_THRESHOLD" not in entities:
            return []

        text_lower = text.lower()

        # 1. 6-digit numbers or SSNs
        condition1 = [
            RecognizerResult("HIPAA_HITECH_LOW_THRESHOLD", m.start(), m.end(), 0.8)
            for m in self.NUMBER_PATTERN.finditer(text)
        ] + [
            RecognizerResult("HIPAA_HITECH_LOW_THRESHOLD", m.start(), m.end(), 0.95)
            for m in self.SSN_PATTERN.finditer(text)
        ]

        # 2. Diseases, Procedures, Drugs, Ingredients
        condition2 = []
        seen_offsets = set()
        for end, (term, typ) in self.automaton.iter(text_lower):
            start = end - len(term) + 1
            if (start, end) not in seen_offsets:
                condition2.append(
                    RecognizerResult("HIPAA_HITECH_LOW_THRESHOLD", start, end + 1, 1.0)
                )
                seen_offsets.add((start, end))

        # 3. Proper names
        condition3 = [
            RecognizerResult("HIPAA_HITECH_LOW_THRESHOLD", m.start(), m.end(), 0.7)
            for m in self.NAME_PATTERN.finditer(text)
        ]

        # 4. US dates with DOB/DOS
        condition4 = [
            RecognizerResult("HIPAA_HITECH_LOW_THRESHOLD", m.start(1), m.end(1), 0.85)
            for m in self.DATE_PATTERN.finditer(text)
        ]

        if condition1 and condition2 and condition3 and condition4:
            results = condition1 + condition2 + condition3 + condition4
            return self._filter_overlaps(results)

        return []

    def _filter_overlaps(self, results: List[RecognizerResult]) -> List[RecognizerResult]:
        results.sort(key=lambda x: (x.start, -x.score))
        filtered = []
        last_end = -1
        for res in results:
            if res.start >= last_end:
                filtered.append(res)
                last_end = res.end
        return filtered

