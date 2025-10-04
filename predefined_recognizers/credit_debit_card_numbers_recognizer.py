import re
from typing import Optional, List
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
import logging

logger = logging.getLogger("presidio-analyzer")

class DatotelCreditDebitCardRecognizer(PatternRecognizer):
    logger.info("Initializing Datotel Custom Credit/Debit Card Recognizer...")

    PATTERNS = [
        # Standard 16-digit cards
        Pattern(
            "Credit/Debit Card - Formatted",
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            0.5
        ),
        Pattern(
            "Credit/Debit Card - Unformatted",
            r"\b\d{16}\b",
            0.5
        ),
        # American Express (15 digits)
        Pattern(
            "Amex Card - Formatted",
            r"\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b",
            0.5
        ),
        Pattern(
            "Amex Card - Unformatted",
            r"\b3[47]\d{13}\b",
            0.5
        )
    ]

    CONTEXT_TERMS = [
        "credit", "debit", "card", "visa", "mastercard", "amex", "american express",
        "discover", "jcb", "diners club", "expiration", "expiry", "valid thru", 
        "valid from", "cvv", "cvc", "cid", "security code", "card number", 
        "cardholder", "card holder", "account number", "banking", "issuer", "csv",
        "expiry date", "bankleitzahl", "handelsbanken", "card verification", 
        "billing", "payment", "credit card", "debit card", "card type", 
        "card details", "card information", "card issuer", "card network",
        "master card", "amex card", "visa card", "card security", "card expiry",
        "card expiration", "card verification value", "card verification code"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "DATOTEL_CARD",
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT_TERMS
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )
        # Precompile context regex for whole-word matching
        escaped_terms = map(re.escape, self.CONTEXT_TERMS)
        pattern = r"\b(" + "|".join(escaped_terms) + r")\b"
        self.context_regex = re.compile(pattern, re.IGNORECASE)

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts=None
    ) -> List[RecognizerResult]:
        logger.info(f"Analyzing text for Datotel Custom Credit/Debit Card: {text}")
        results = super().analyze(text, entities, nlp_artifacts)
        total_cards = len(results)
        logger.info(f"Found {total_cards} card numbers in text")

        for result in results:
            # Extract card number from text
            card_number = text[result.start:result.end]
            logger.debug(f"Processing card number: {card_number}")

            # Create context window around the card number
            window_size = 20
            start_index = max(0, result.start - window_size)
            end_index = min(len(text), result.end + window_size)
            nearby_text = text[start_index:end_index]

            # Check for context terms in the window
            has_context = bool(self.context_regex.search(nearby_text))
            logger.debug(f"Context near card: {has_context}")

            # Calculate base score
            base_score = 0.71 if has_context else 0.5
            logger.debug(f"Base score: {base_score}")

            # Apply multi-card boost if needed
            if total_cards > 1:
                # Add 0.5 for each additional card (capped at 1.0)
                adjusted_score = base_score + 0.5 * (total_cards - 1)
                result.score = min(adjusted_score, 1.0)
                logger.debug(f"Multi-card boost applied: {result.score}")
            else:
                result.score = base_score

            logger.info(f"Final score for card: {result.score}")

        return results
