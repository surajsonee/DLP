from typing import Optional, List, Tuple
from presidio_analyzer import Pattern, PatternRecognizer

class MedicalNumberRecognizer(PatternRecognizer):
    """
    Recognizes Medical Numbers (NPI or OPNI).

    Medical Numbers are alphanumeric codes with specific formatting rules.
    This recognizer identifies NPI or OPNI followed by 10 digits using regex.
    """

    PATTERNS = [
            Pattern(
                name="NPI_pattern",
                # Matches 'NPI' (case-insensitive) followed by separator and 10 digits
                regex=r"(?i)\bNPI[ :;\-]\s*\d{10}\b",
                score=1.0,  # High confidence
            ),
            Pattern(
                name="OPNI_pattern",
                # Matches 'OPNI' (case-insensitive) followed by separator and 10 digits
                regex=r"(?i)\bOPNI[ :;\-]\s*\d{10}\b",
                score=1.0,  # High confidence
            )
        ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        supported_language: str = "en",
        supported_entity: str = "MEDICAL_NUMBER",
    ):
        patterns = patterns if patterns else self.PATTERNS
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            supported_language=supported_language,
        )
