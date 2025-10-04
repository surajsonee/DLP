from typing import Optional, List, Tuple
from presidio_analyzer import Pattern, PatternRecognizer

class HICNRecognizer(PatternRecognizer):
    """
    Recognizes Health Insurance Claim Numbers (HICNs).

    HICNs are alphanumeric codes typically formatted as:
    - A letter followed by 6 or 9 digits
    - 9 digits followed by 1 or 2 letters
    - 9 digits followed by a letter and another digit

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    """

    PATTERNS = [
        Pattern(
            "HICN (High)",
            r"\b[A-Z][0-9]{6}\b|\b[0-9]{9}[A-Z]{1,2}\b|\b[0-9]{9}[A-Z][0-9]\b",
            0.85,
        ),
        # New patterns based on the provided regex expressions
        Pattern(
            "HICN (Pattern 1)",
            r"\b[A-Z]{0,3}[0-9]{9}[0-9A-Z]{1,3}\b",  # Alphanumeric string, no delimiters
            1.0,
        ),
        Pattern(
            "HICN (Pattern 2)",
            r"\b[A-Z]{0,3}[0-9]{3} [0-9]{6}[0-9A-Z]{1,3}\b",  # Alphanumeric string with space delimiter
            1.0,
        ),
        Pattern(
            "HICN (Pattern 3)",
            r"\b[A-Z]{0,3}-[0-9]{3} [0-9]{2}-[0-9]{4}-[0-9A-Z]{1,3}\b",  # Alphanumeric string with space and hyphen delimiters
            1.0,
        ),
        Pattern(
            "HICN (Pattern 4)",
            r"\b[A-Z]{0,3}-[0-9]{3}-[0-9]{2}-[0-9]{4}-[0-9A-Z]{1,3}\b",  # Alphanumeric string with hyphen delimiters
            1.0,
        ),
    ]

    CONTEXT = [
        "health insurance claim number",
        "hicn",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "HICN",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )