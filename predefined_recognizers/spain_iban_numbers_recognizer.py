from typing import Optional, List
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
import logging

logger = logging.getLogger("presidio-analyzer")

class SpainIBANRecognizer(PatternRecognizer):
    logger.info("Initializing Spain IBAN Recognizer...")

    # Define patterns for Spanish IBAN
    PATTERNS = [
        Pattern(
            "Spain IBAN - High Confidence",
            r"\bES\d{2}\s?\d{4}\s?\d{4}\s?\d{2}\s?\d{10}\b",  # Pattern to match: 'ES', 2 digits (checksum), 4 digits (bank code), 4 digits (branch code), 2 digits (check digits), 10 digits (account number)
            0.7  # Initial confidence score for the pattern match
        ),
    ]

    # Spanish and English context keywords for IBAN
    CONTEXT = [
        "IBAN", "international bank account number", "número de cuenta bancaria", 
        "número IBAN", "IBAN de España", "account number", "bank account"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",  # Supports Spanish and English
        supported_entity: str = "SPAIN_IBAN",
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts=None
    ) -> List[RecognizerResult]:
        results = super().analyze(text, entities, nlp_artifacts)
        for result in results:
            # Increase the score if context keywords are found
            if any(keyword in text.lower() for keyword in self.CONTEXT):
                result.score = min(result.score + 0.3, 1.0)  # Increase score by 0.3, cap at 1.0
        return results
