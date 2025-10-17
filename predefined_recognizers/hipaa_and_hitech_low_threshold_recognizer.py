import os
import re
import json
import logging
from typing import List
from presidio_analyzer import RecognizerResult, LocalRecognizer
from ahocorasick import Automaton

# Configure logger
logger = logging.getLogger("LowThresholdHIPAARecognizer")
logger.setLevel(logging.DEBUG)  # change to INFO or ERROR in production
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(message)s")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


class LowThresholdHIPAARecognizer(LocalRecognizer):
    """
    Self-contained recognizer for HIPAA Low Threshold policy.

    Detects text containing:
      1. ≥6-digit numbers or SSNs (with/without dashes/spaces)
      2. Medical term (disease, procedure, or drug)
      3. Proper name
      4. Date (any common format, optionally preceded by Date/DOB/DOS)
    """

    def __init__(self, supported_language="en"):
        super().__init__(
            supported_entities=["HIPAA_HITECH_LOW_THRESHOLD"],
            supported_language=supported_language,
        )

        # --- 1️⃣ Numeric & SSN Patterns ---
        self.NUMBER_PATTERN = re.compile(r"\b\d{6,}\b")
        self.SSN_PATTERN = re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b")

        # --- 2️⃣ Date Patterns ---
        self.DATE_PATTERN = re.compile(
            r"\b(?:DOB|DOS|Date(?: of Birth| of Service)?|Date)\b[:\s]*"
            r"("
            r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|"          # 03-28-2023 or 28/03/2023
            r"(?:\d{4}[/-]\d{1,2}[/-]\d{1,2})|"            # 2023-03-28
            r"(?:\d{1,2}\.\d{1,2}\.\d{2,4})|"              # 28.03.2023
            r"(?:\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s\d{2,4})|"  # 28 Mar 2023
            r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s\d{1,2},?\s\d{2,4})"  # Mar 28 2023
            r")",
            re.IGNORECASE,
        )

        # --- 3️⃣ Proper Name Pattern ---
        self.NAME_PATTERN = re.compile(r"\b[A-Z][a-z]+(?:[-'\s][A-Z][a-z]+)+\b")

        # --- 4️⃣ Medical Terms Dictionary via Aho-Corasick ---
        self.automaton = Automaton()
        self._load_medical_terms()

    def _load_medical_terms(self):
        """Loads ICD and drug dictionaries for disease/drug detection."""
        base_path = "/usr/share/data"

        def safe_load(filename):
            try:
                with open(os.path.join(base_path, filename), encoding="utf-8") as f:
                    data = json.load(f)
                    logger.debug(f"Loaded {len(data)} records from {filename}")
                    return data
            except Exception as e:
                logger.warning(f"Failed to load {filename}: {e}")
                return []

        try:
            # ICD-9
            for item in safe_load("ValidICD9-Jan2024.json"):
                desc = item.get("LONG DESCRIPTION (VALID ICD-9 FY2024)", "")
                if desc:
                    self.automaton.add_word(desc.lower(), desc)

            # ICD-10
            for item in safe_load("ValidICD10-Jan2024.json"):
                for key in [
                    "SHORT DESCRIPTION (VALID ICD-10 FY2024)",
                    "LONG DESCRIPTION (VALID ICD-10 FY2024)",
                ]:
                    if item.get(key):
                        self.automaton.add_word(item[key].lower(), item[key])

            # Drugs
            for drug in safe_load("Drugs.json"):
                self.automaton.add_word(drug.lower(), drug)

            # Ingredients
            for ing in safe_load("Ingredients.json"):
                self.automaton.add_word(ing.lower(), ing)

            self.automaton.make_automaton()
            logger.info("✅ Medical term automaton built successfully")

        except Exception as e:
            logger.error(f"Failed to build medical automaton: {e}")

    # --- Analyzer Core ---
    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        """Analyze text for HIPAA low threshold detection."""
        if "HIPAA_HITECH_LOW_THRESHOLD" not in entities:
            return []

        logger.debug(f"Analyzing text: {text}")

        text_lower = text.lower()

        # 1️⃣ Numeric / SSN
        condition1 = []
        for m in self.NUMBER_PATTERN.finditer(text):
            logger.debug(f"✅ Found 6+ digit number: '{text[m.start():m.end()]}'")
            condition1.append(
                RecognizerResult("HIPAA_HITECH_LOW_THRESHOLD", m.start(), m.end(), 0.8)
            )
        for m in self.SSN_PATTERN.finditer(text):
            logger.debug(f"✅ Found SSN: '{text[m.start():m.end()]}'")
            condition1.append(
                RecognizerResult("HIPAA_HITECH_LOW_THRESHOLD", m.start(), m.end(), 0.95)
            )

        # 2️⃣ Medical terms
        condition2 = []
        seen_offsets = set()
        for end, term in self.automaton.iter(text_lower):
            start = end - len(term) + 1
            if (start, end) not in seen_offsets:
                logger.debug(f"✅ Found medical term: '{term}'")
                condition2.append(
                    RecognizerResult("HIPAA_HITECH_LOW_THRESHOLD", start, end + 1, 1.0)
                )
                seen_offsets.add((start, end))

        # 3️⃣ Proper names
        condition3 = []
        for m in self.NAME_PATTERN.finditer(text):
            name = text[m.start():m.end()]
            logger.debug(f"✅ Found proper name: '{name}'")
            condition3.append(
                RecognizerResult("HIPAA_HITECH_LOW_THRESHOLD", m.start(), m.end(), 0.7)
            )

        # 4️⃣ Dates
        condition4 = []
        for m in self.DATE_PATTERN.finditer(text):
            date_str = text[m.start(1):m.end(1)]
            logger.debug(f"✅ Found date: '{date_str}'")
            condition4.append(
                RecognizerResult("HIPAA_HITECH_LOW_THRESHOLD", m.start(1), m.end(1), 0.85)
            )

        # --- Summary logging ---
        logger.info(
            f"Matches → Numbers/SSNs: {len(condition1)}, "
            f"Medical Terms: {len(condition2)}, Names: {len(condition3)}, Dates: {len(condition4)}"
        )

        # --- Require one match from each category ---
        if condition1 and condition2 and condition3 and condition4:
            results = condition1 + condition2 + condition3 + condition4
            logger.info("✅ All four conditions met — returning results")
            return self._filter_overlaps(results)

        logger.warning("❌ One or more required conditions not met — no results returned")
        return []

    def _filter_overlaps(self, results: List[RecognizerResult]) -> List[RecognizerResult]:
        """Remove overlapping recognizer results, keeping highest scoring ones."""
        results.sort(key=lambda x: (x.start, -x.score))
        filtered = []
        last_end = -1
        for res in results:
            if res.start >= last_end:
                filtered.append(res)
                last_end = res.end
        return filtered

