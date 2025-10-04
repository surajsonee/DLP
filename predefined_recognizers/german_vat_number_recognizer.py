import re
from functools import reduce
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
from typing import List, Optional

class GermanVATRecognizer(PatternRecognizer):
    """
    Recognizer to detect and validate German VAT numbers (USt-IdNr):
      – Format: 'DE' + 9 digits
      – Checksum algorithm as per EU specification
      – Context enforcement on terms like 'VAT', 'Mehrwertsteuer', etc.
    """

    # Only allow the 'DE' + 9 digits format
    PATTERNS = [
        Pattern(
            name="German VAT (DE + 9 digits)",
            regex=r"\bDE[0-9]{9}\b",
            score=1.0,
        ),
    ]

    # VAT-related context keywords
    CONTEXT = [
        "vat number", "vat no", "vat#", "mwst", "mehrwertsteuer",
        "mehrwertsteuer identifikationsnummer",
    ]

    # Minimum score required to surface a finding
    MIN_SCORE = 0.85

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "DE_Germany_VAT_Number",
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns or self.PATTERNS,
            context=context or self.CONTEXT,
            supported_language=supported_language,
        )

    def analyze(
        self,
        text: str,
        entities: List[str],
        nlp_artifacts=None
    ) -> List[RecognizerResult]:
        # 1. Base pattern match
        results = super().analyze(text, entities, nlp_artifacts)

        filtered: List[RecognizerResult] = []
        for res in results:
            span = text[res.start : res.end]  # e.g. "DE123456789"

            # 2. Check context and checksum
            has_ctx = self._has_context(text, res.start, res.end)
            valid_ck = self._validate_checksum(span)

            if has_ctx and valid_ck:
                # boost to maximum
                res.score = 1.0
            else:
                # penalize stray or invalid matches
                res.score *= 0.5

            # 3. Only keep high-confidence hits
            if res.score >= self.MIN_SCORE:
                filtered.append(res)

        return filtered

    def _has_context(self, text: str, start: int, end: int) -> bool:
        """
        Look in a 300-char window around the candidate for any VAT context keyword.
        """
        window = text[max(0, start - 300) : end + 300].lower()
        return any(ctx in window for ctx in self.CONTEXT)

    def _validate_checksum(self, vat: str) -> bool:
        """
        German VAT checksum (USt-IdNr) validation:

          1. Strip 'DE' prefix, work on the 9 digits.
          2. Initialize product = 10.
          3. For digits 1..8:
               sum = (digit + product) % 10
               if sum == 0: sum = 10
               product = (2 * sum) % 11
          4. check_digit = 11 - product
             if check_digit == 10: return False
             if check_digit == 11: check_digit = 0
          5. Return (check_digit == digit9)

        Source: vat-validator library implementation :contentReference[oaicite:0]{index=0}
        """
        # Ensure format: DE + 9 digits
        match = re.fullmatch(r"DE(\d{9})", vat)
        if not match:
            return False

        digits = list(map(int, match.group(1)))
        # First 8 digits → for the running product
        p = reduce(
            lambda product, d: (2 * (10 if (d + product) % 10 == 0 else (d + product) % 10)) % 11,
            digits[:-1],
            10,
        )

        # Compute expected check digit
        r = 11 - p
        if r == 10:
            return False
        if r == 11:
            r = 0

        # Compare to the 9th digit
        return r == digits[-1]
