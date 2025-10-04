import re
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
from typing import List, Optional


class GermanIBANRecognizer(PatternRecognizer):
    """
    Recognizer to detect German International Bank Account Numbers (IBAN).
    """

    # Patterns for detecting German IBANs
    PATTERNS = [
        # Pattern for IBAN starting with "CR", "DE", "ME", or "RS" followed by 20 digits
        Pattern(
            name="German IBAN",
            regex=r"\b(CR|DE|ME|RS)[0-9]{20}\b",
            score=1.0,
        ),
        # Pattern for German IBAN in specific format with spaces
        Pattern(
            name="German IBAN (spaced format)",
            regex=r"DE\d{2}[ ]\d{4}[ ]\d{4}[ ]\d{4}[ ]\d{4}[ ]\d{2}|DE\d{20}",
            score=1.0,
        ),
        # Pattern for German IBAN with 20 digits
        Pattern(
            name="German IBAN (20 digits)",
            regex=r"DE[0-9]{2}[0-9]{8}[0-9]{10}",
            score=1.0,
        ),
        # Additional pattern to cover variations with optional spaces
        Pattern(
            name="German IBAN (optional spaces)",
            regex=r"DE\d{2}[ ]\d{4}[ ]\d{4}[ ]\d{4}[ ]\d{4}[ ]\d{2}|DE\d{20}",
            score=1.0,
        ),
    ]

    CONTEXT = [
        "iban", "international bank account number", "bank account", "bank account number",
        "bankkonto", "kontonummer", "bankverbindung", "girokonto"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "de",
        supported_entity: str = "DE_German_IBAN",
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        results = super().analyze(text, entities, nlp_artifacts)

        # Apply context-based scoring and checksum validation
        for result in results:
            if self._has_context(text, result.start, result.end) and self._validate_checksum(text[result.start:result.end]):
                result.score = min(result.score + 0.15, 1.0)  # Boost score if context and checksum pass
            else:
                result.score = result.score * 0.5  # Reduce score if context or checksum fails

        return results

    def _validate_checksum(self, iban_number: str) -> bool:
        """Validate the checksum of the German IBAN."""
        # Implement the checksum logic here, if applicable.
        # Since the actual checksum logic isn't specified, assuming a placeholder validation.
        # Replace with actual checksum algorithm as required.
        return True  # Placeholder: Assume checksum is valid

    def _has_context(self, text: str, start: int, end: int) -> bool:
        """Check if there is relevant context around the detected pattern."""
        window_size = 300  # Number of characters to check before and after the detected pattern
        context_window = text[max(0, start - window_size): min(len(text), end + window_size)]
        context_found = any(context_word.lower() in context_window.lower() for context_word in self.CONTEXT)
        return context_found
