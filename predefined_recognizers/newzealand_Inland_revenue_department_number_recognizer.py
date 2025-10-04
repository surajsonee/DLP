from typing import Optional, List
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
import logging
import re

logger = logging.getLogger("presidio-analyzer")

class NewZealandInlandRevenueDepartmentNumberRecognizer(PatternRecognizer):
    logger.info("Initializing Eight or Nine Digit NewZealandInlandRevenueDepartmentNumberRecognizer...")

    # Define patterns for eight or nine digits with optional delimiters (spaces or hyphens)
    PATTERNS = [
        Pattern(
            "Eight or Nine Digit Number - Medium Confidence",
            r"^\d{2}\s\d{3}\s\d{3}$",  # Pattern for 8 or 9 digits with optional spaces/hyphens
            0.7  # Initial confidence score for the pattern match
        ),
        Pattern(
            "Eight or Nine Digit Number - Medium Confidence",
            r"\b[0-1]?[0-9]{8}\b",  # Pattern for 8 or 9 digits with optional spaces/hyphens
            1.0  # Initial confidence score for the pattern match
        ),
        Pattern(
            "Eight or Nine Digit Number - Medium Confidence",
            r"\b[0-1]?[0-9]{2}-[0-9]{3}-[0-9]{3}\b",  # Pattern for 8 or 9 digits with optional spaces/hyphens
            1.0  # Initial confidence score for the pattern match
        ),
    ]

    # Context keywords for the number
    CONTEXT = ["ird no.", "ird no#", "nz ird", "new zealand ird", "ird number", "inland revenue number", "IRD number", "Inland Revenue Department number", "tax number", "New Zealand tax number", "New Zealand IRD", "IRD", "NZ IRD", "taxpayer identification", "Inland Revenue", "NZ tax ID", "taxpayer number"]


    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",  # Supports English (can be modified for other languages)
        supported_entity: str = "NewZealand_Inland_Revenue_Department_Number",
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
        logger.info(f"Analyzing text for eight or nine digit number: {text}")
        results = super().analyze(text, entities, nlp_artifacts)
        for result in results:
            number = text[result.start:result.end]
            cleaned_number = re.sub(r"[-\s]", "", number)  # Remove delimiters for checksum validation
            logger.debug(f"Detected Number: {number}, Cleaned Number: {cleaned_number}, Confidence: {result.score}")
            if self._is_valid_checksum(cleaned_number):
                logger.info(f"Checksum valid for number: {cleaned_number}")
                result.score = 0.7  # Medium confidence if checksum passes
                if any(keyword in text.lower() for keyword in self.CONTEXT):
                    logger.info(f"Context keywords found for number: {number}, setting high confidence.")
                    result.score = 1.0  # High confidence if context keywords are present
            else:
                logger.warning(f"Invalid checksum for number: {number}")
                result.score = 0.0  # Invalid number
        return results

    def _is_valid_checksum(self, number: str) -> bool:
        """
        Validate the checksum for the given number.
        Custom checksum logic can be defined as per requirements.
        This example uses a Modulus 11 checksum algorithm.
        """
        logger.debug(f"Validating checksum for number: {number}")
        total_sum = 0
        multiplier = len(number)  # Dynamically adjust the multiplier based on the length of the number (8 or 9)

        for i in range(len(number)):
            digit = int(number[i])
            total_sum += digit * multiplier
            multiplier -= 1

        # Modulus 11 check
        is_valid = total_sum % 11 == 0
        if is_valid:
            logger.info(f"Checksum for number {number} is valid.")
        else:
            logger.error(f"Checksum for number {number} is invalid.")
        return is_valid
        
