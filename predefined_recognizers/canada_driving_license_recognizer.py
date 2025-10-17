import re
import logging
from typing import Optional, List
from presidio_analyzer import Pattern, PatternRecognizer

# Enable detailed debug logs
logger = logging.getLogger("presidio-analyzer")
logger.setLevel(logging.DEBUG)


class CanadaDriversLicenceRecognizer(PatternRecognizer):
    """
    Recognizer for Canadian Driver's Licence numbers across all provinces and territories.
    Dynamically scores matches based on validation checks.
    """

    # ---------------------------
    # Regex Patterns (by Province)
    # ---------------------------
    PATTERNS = [
        # Alberta: 6 digits + hyphen + 3 digits, or 5–9 digits
        Pattern("Alberta DL", r"\b\d{6}-\d{3}\b|\b\d{5,9}\b", 0.8),

        # British Columbia: 7 digits
        Pattern("British Columbia DL", r"\b\d{7}\b", 0.75),

        # Manitoba: 2 letters - 2 letters - 2 letters - 1 letter + 3 digits + 2 letters (complex)
        Pattern("Manitoba DL", r"\b[A-Z]{2}-?[A-Z]{2}-?[A-Z]{2}-?[A-Z]\d{3}[A-Z]{2}\b", 0.85),

        # New Brunswick: 5–7 digits
        Pattern("New Brunswick DL", r"\b\d{5,7}\b", 0.75),

        # Newfoundland and Labrador: 1 letter + 9 digits
        Pattern("Newfoundland and Labrador DL", r"\b[A-Z]\d{9}\b", 0.9),

        # Nova Scotia: 5 letters - optional hyphen - 9 digits (specific digit rules simplified)
        Pattern("Nova Scotia DL", r"\b[A-Z]{5}-?\d{9}\b", 0.85),

        # Ontario: 1 letter + 4 digits + optional hyphen + 5 digits + province-specific suffix
        Pattern("Ontario DL", r"\b[A-Z]\d{4}-?\d{5}\d[0156]\d[0-3]\d\b", 0.9),

        # Prince Edward Island: 5–6 digits
        Pattern("Prince Edward Island DL", r"\b\d{5,6}\b", 0.7),

        # Quebec: 1 letter + 12 digits
        Pattern("Quebec DL", r"\b[A-Z]\d{12}\b", 0.9),

        # Saskatchewan: 8 digits
        Pattern("Saskatchewan DL", r"\b\d{8}\b", 0.8),

        # Northwest Territories, Yukon, Nunavut: 6–9 alphanumeric, must contain at least 1 digit
        Pattern("Territories DL", r"\b(?=.*\d)[A-Z0-9]{6,9}\b", 0.65),
    ]

    CONTEXT = [
        "driver licence",
        "drivers license",
        "driving licence",
        "dl number",
        "canada licence",
        "provincial licence",
        "issued by",
        "transport",
        "vehicle licence",
        "dl no",
    ]

    # ---------------------------------------
    # Init with defaults and optional override
    # ---------------------------------------
    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_entity: str = "CANADA_DRIVERS_LICENCE",
        supported_language: str = "en",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT

        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )

    # ------------------------------------------
    # Validation and Scoring Logic per Match
    # ------------------------------------------
    def validate_result(self, pattern_text: str) -> bool:
        """
        Lightweight validation logic for each matched DL number.
        Returns True if valid format, False otherwise.
        """
        clean_text = re.sub(r"[^A-Za-z0-9]", "", pattern_text)
        logger.debug(f"[VALIDATE] Raw: '{pattern_text}' | Cleaned: '{clean_text}'")

        if len(clean_text) < 5 or len(clean_text) > 15:
            logger.debug(f"[INVALID] Length out of range ({len(clean_text)})")
            return False

        # Must have at least 5 characters and either digits or letters
        if not re.search(r"[0-9]", clean_text):
            logger.debug("[INVALID] Missing digits")
            return False

        # Province-specific lightweight validation rules
        if re.match(r"^\d{6}\d{3}$", clean_text) or re.match(r"^\d{6}-\d{3}$", pattern_text):
            logger.debug("[VALID] Alberta format")
            return True
        if re.match(r"^[A-Z]\d{12}$", clean_text):
            logger.debug("[VALID] Quebec format")
            return True
        if re.match(r"^\d{8}$", clean_text):
            logger.debug("[VALID] Saskatchewan format")
            return True
        if re.match(r"^\d{7}$", clean_text):
            logger.debug("[VALID] BC or NB format")
            return True
        if re.match(r"^[A-Z]\d{9}$", clean_text):
            logger.debug("[VALID] Newfoundland format")
            return True

        logger.debug("[UNCERTAIN] Could be generic Territories or unknown province")
        return True  # still a possible match

    def analyze(self, text, entities, nlp_artifacts=None):
        """
        Override to dynamically adjust score after validation.
        """
        results = super().analyze(text, entities, nlp_artifacts)
        for result in results:
            matched_text = text[result.start:result.end]
            is_valid = self.validate_result(matched_text)
            old_score = result.score
            result.score = max(0.7, old_score) if is_valid else min(0.69, old_score - 0.1)
            logger.debug(
                f"[RESULT] '{matched_text}' | Valid={is_valid} | "
                f"OldScore={old_score:.2f} → NewScore={result.score:.2f}"
            )
        return results

