import re
import logging
from typing import Optional, List
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult

logger = logging.getLogger("presidio-analyzer")
logger.setLevel(logging.DEBUG)


class DatotelCreditDebitCardRecognizer(PatternRecognizer):
    logger.info("Initializing Datotel Custom Credit/Debit Card Recognizer...")

    PATTERNS = [
        # Standard 16-digit cards
        Pattern("Credit/Debit Card - Formatted", r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", 0.5),
        Pattern("Credit/Debit Card - Unformatted", r"\b\d{16}\b", 0.5),

        # American Express (15 digits)
        Pattern("Amex Card - Formatted", r"\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b", 0.5),
        Pattern("Amex Card - Unformatted", r"\b3[47]\d{13}\b", 0.5),
    ]

    CONTEXT_TERMS = [
        "credit", "debit", "card", "visa", "mastercard", "amex", "american express",
        "discover", "jcb", "diners club", "expiration", "expiry", "valid thru",
        "valid from", "cvv", "cvc", "cid", "security code", "card number",
        "cardholder", "card holder", "account number", "banking", "issuer", "csv",
        "expiry date", "card verification", "billing", "payment", "credit card",
        "debit card", "card type", "card details", "card information", "card issuer",
        "card network", "master card", "amex card", "visa card", "card security",
        "card expiry", "card expiration", "card verification value", "card verification code"
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

        # Precompile regex for faster context search
        escaped_terms = map(re.escape, self.CONTEXT_TERMS)
        pattern = r"\b(" + "|".join(escaped_terms) + r")\b"
        self.context_regex = re.compile(pattern, re.IGNORECASE)

    # ----------------------------------------------------------------------
    # Helper: Luhn check
    # ----------------------------------------------------------------------
    @staticmethod
    def luhn_check(card_number: str) -> bool:
        digits = [int(d) for d in card_number if d.isdigit()]
        checksum = 0
        parity = len(digits) % 2
        for i, d in enumerate(digits):
            if i % 2 == parity:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        is_valid = checksum % 10 == 0
        logger.debug(f"Luhn check for {card_number}: {'Valid' if is_valid else 'Invalid'}")
        return is_valid

    # ----------------------------------------------------------------------
    # Main analysis
    # ----------------------------------------------------------------------
    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        logger.info(f"Analyzing text for Datotel Custom Credit/Debit Card: {text}")
        results = super().analyze(text, entities, nlp_artifacts)
        logger.info(f"Found {len(results)} potential card numbers")

        for result in results:
            card_number = text[result.start:result.end]
            logger.debug(f"Processing card number: {card_number}")

            # Check for nearby context terms
            window_size = 20
            start_index = max(0, result.start - window_size)
            end_index = min(len(text), result.end + window_size)
            nearby_text = text[start_index:end_index]
            has_context = bool(self.context_regex.search(nearby_text))
            logger.debug(f"Context detected near card: {has_context}")

            # Validate via Luhn algorithm
            is_valid = self.luhn_check(card_number)

            # ---------------------------------------------------------------
            # Scoring logic based on your 3 rules:
            # 1️⃣ Keywords + incorrect number       => < 0.7
            # 2️⃣ No keywords + correct number       => > 0.7
            # 3️⃣ Keywords + correct number          => > 0.8 (up to 1.0)
            # ---------------------------------------------------------------
            if has_context and not is_valid:
                score = 0.6
            elif not has_context and is_valid:
                score = 0.75
            elif has_context and is_valid:
                score = 0.9
            else:
                score = 0.5  # fallback: no context + invalid number

            result.score = round(score, 2)
            logger.info(f"Card: {card_number} | Valid: {is_valid} | Context: {has_context} | Final Score: {result.score}")

        return results

