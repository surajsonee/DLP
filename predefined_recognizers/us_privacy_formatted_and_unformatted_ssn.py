from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
from typing import List, Optional


class SSN_Formatted_Unformatted_Recognizer(PatternRecognizer):
    """
    Recognizer to detect US Social Security Numbers (SSNs) based on different formats.
    """

    PATTERNS = [
        # SSN pattern formatted with hyphens (e.g., xxx-xx-xxxx)
        Pattern(
            name="SSN formatted with hyphen",
            regex=r"\b\d{3}-\d{2}-\d{4}\b",
            score=0.85,
        ),
        # SSN pattern formatted with spaces (e.g., xxx xx xxxx)
        Pattern(
            name="SSN formatted with spaces",
            regex=r"\b\d{3} \d{2} \d{4}\b",
            score=0.85,
        ),
        # Unformatted SSN pattern (e.g., xxxxxxxxx)
        Pattern(
            name="SSN unformatted",
            regex=r"\b\d{9}\b",
            score=0.5,
        ),
    ]

    CONTEXT = [
        "social security number",
        "ssa number",
        "social security",
        "ssn",
        "ssn#",
        "social security#",
        "security number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_formatted_unformatted_SSN",
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

        # Apply context-based scoring
        for result in results:
            if self._has_context(text, result.start, result.end):
                result.score = min(result.score + 0.4, 1.0)  # Boost score with context
            else:
                result.score = result.score * 0.5  # Reduce score if no context found

        # Invalidate results that don't meet the criteria
        results = [result for result in results if not self.invalidate_result(text[result.start:result.end])]
        return results

    def _has_context(self, text: str, start: int, end: int) -> bool:
        """Check if there is relevant context around the detected pattern."""
        window_size = 50  # Number of characters to check before and after the detected pattern
        context_window = text[max(0, start - window_size): min(len(text), end + window_size)]
        context_found = any(context_word.lower() in context_window.lower() for context_word in self.CONTEXT)
        return context_found

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Invalidate SSNs that don't meet certain criteria.
        """
        only_digits = "".join(c for c in pattern_text if c.isdigit())

        # Validate length
        if len(only_digits) != 9:
            return True

        return False
