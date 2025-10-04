from typing import Optional, List, Tuple
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult


class DateOfBirthRecognizer(PatternRecognizer):
    """
    Recognizes Date of Birth (DOB) and Date of Service (DOS) in close proximity to specific phrases.

    This recognizer identifies DOB and DOS using regex and context words.
    Reference: Custom rules.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    PATTERNS = [
        Pattern("Date of Birth (High)", r"\b(?i)(\d{1,2}[-./]\d{1,2}[-./]\d{4})\b", 0.85),
        Pattern("Date of Birth (Medium)", r"\b(?i)(\d{1,2}[-./]\d{1,2}[-./]\d{2})\b", 0.6),
    ]

    CONTEXT = [
        "date of birth",
        "dob",
        "date of service",
        "dos",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "DATE_OF_BIRTH",
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
        filtered_results = []

        # Filter results to only include those with a context match
        for result in results:
            if self._has_context(text, result.start, result.end):
                filtered_results.append(result)

        return filtered_results

    def _has_context(self, text: str, start: int, end: int) -> bool:
        """
        Check if there is relevant context around the detected pattern.

        This method checks if any context words appear in proximity to the detected pattern.
        """
        window_size = 50  # Number of characters to check before and after the detected pattern
        context_window = text[max(0, start - window_size): min(len(text), end + window_size)]
        context_found = any(context_word.lower() in context_window.lower() for context_word in self.CONTEXT)
        return context_found
