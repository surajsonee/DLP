from typing import Optional, List
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
import logging
import re

logger = logging.getLogger("presidio-analyzer")

class CreditCardRecognizer(PatternRecognizer):
    logger.info("Initializing Credit Card Recognizer...")

    # Define patterns for credit cards starting with 45 or 67
    PATTERNS = [
        Pattern(
            "Credit Card - Starts with 45",
            r"\b45\d{3}(\s|-)?\d{4}(\s|-)?\d{4}(\s|-)?\d{4}\b",  # Pattern for credit card starting with 45
            0.5  # Initial confidence score for the pattern match
        ),
		Pattern(
		"Credit Card - Starts with 45",
		r"\b45\d{14}\b|\b45\d{3}(\s|-)?\d{4}(\s|-)?\d{4}(\s|-)?\d{4}\b",  # Matches plain 16 digits or formatted with spaces/hyphens
		0.5
		),
		Pattern(
		"Credit Card - Starts with 67",
		r"\b67\d{14}\b|\b67\d{3}(\s|-)?\d{4}(\s|-)?\d{4}(\s|-)?\d{4}\b",  # Matches plain 16 digits or formatted with spaces/hyphens
		0.5
		) 
        
    ]

    # Context keywords for credit cards
    CONTEXT = [
        "credit card", "card number", "payment card", "CCN", "cardholder", "card details", "bank card"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",  # Supports English
        supported_entity: str = "45_67_CREDIT_CARD",
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
        logger.info(f"Analyzing text for Credit Card: {text}")
        results = super().analyze(text, entities, nlp_artifacts)

        for result in results:
            card_number = text[result.start:result.end]
            logger.debug(f"Detected Credit Card Number: {card_number}, Confidence: {result.score}")

            # Remove spaces or hyphens for checksum validation
            cleaned_card_number = re.sub(r"[\s-]", "", card_number)

            # Perform Luhn checksum validation
            if self._is_valid_checksum(cleaned_card_number):
                logger.info(f"Checksum valid for Credit Card: {card_number}")
                result.score = 0.7  # Medium confidence if checksum passes
                # Check for context keywords
                if any(keyword in text.lower() for keyword in self.CONTEXT):
                    logger.info(f"Context keywords found near Credit Card: {card_number}, setting high confidence.")
                    result.score = 1.0  # High confidence if context keywords are present
            else:
                logger.warning(f"Invalid checksum for Credit Card: {card_number}")
                result.score = 0.0  # Invalid credit card number
            
        return results

    def _is_valid_checksum(self, card_number: str) -> bool:
        """
        Validate the checksum using Luhn's algorithm (Modulus 10).
        """
        sum_ = 0
        alternate = False

        for digit in reversed(card_number):
            num = int(digit)
            if alternate:
                num *= 2
                if num > 9:
                    num -= 9
            sum_ += num
            alternate = not alternate

        return sum_ % 10 == 0
