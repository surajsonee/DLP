from typing import Optional, List
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
import logging
import re

logger = logging.getLogger("presidio-analyzer")

class SpainVATRecognizer(PatternRecognizer):
    logger.info("Initializing Spain VAT Number Recognizer...")

    # Define patterns for Spanish VAT Numbers (companies and individuals)
    PATTERNS = [
        Pattern(
            "Spain VAT - Company Format",
            r"\bES[A-Za-z]\d{8}\b|\bES[A-Za-z]\d{7}[A-Za-z]\b",  # Pattern for company VAT: ES+letter+8 digits or ES+letter+7 digits+letter
            0.5  # Initial confidence score for the pattern match
        ),
        Pattern(
            "Spain VAT - Individual Format",
            r"\bES\d{8}[A-Za-z]\b|\bES[A-Za-z]\d{7}[A-Za-z]\b",  # Pattern for individual VAT: ES+8 digits+letter (Spaniards) or ES+letter+7 digits+letter (foreigners)
            0.5  # Initial confidence score for the pattern match
        )
    ]

    # Context keywords for VAT
    CONTEXT = [
        "VAT", "IVA", "número de IVA", "VAT number", 
        "número de identificación fiscal", "número de registro fiscal"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",  # Supports Spanish and English
        supported_entity: str = "SPAIN_VAT_NUMBER",
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
        logger.info(f"Analyzing text: {text}")
        results = super().analyze(text, entities, nlp_artifacts)
        for result in results:
            vat_number = text[result.start:result.end]
            logger.debug(f"Detected VAT Number: {vat_number}, Confidence: {result.score}")
            # Set confidence level based on whether context keywords are present
            if any(keyword in text.lower() for keyword in self.CONTEXT):
                logger.info(f"Context keywords found for VAT Number: {vat_number}, setting high confidence.")
                result.score = 1.0  # High confidence if context keywords are present
            else:
                result.score = 0.7  # Medium confidence without context keywords
        return results
