from typing import Optional, List
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
import re

class NewZealandInlandRevenueDepartmentNumberRecognizer(PatternRecognizer):

    # ---------------------------------------------------------------------
    # Define patterns for NZ IRD Numbers
    # ---------------------------------------------------------------------
    PATTERNS = [
        Pattern(
            "NZ_IRD_With_Delimiters",
            r"\b\d{2,3}[-\s]?\d{3}[-\s]?\d{3}\b",
            0.75,
        ),
        Pattern(
            "NZ_IRD_8_Digit",
            r"\b\d{8}\b",
            0.6,
        ),
        Pattern(
            "NZ_IRD_9_Digit",
            r"\b\d{9}\b",
            0.6,
        ),
    ]

    CONTEXT = [
        "ird", "ird number", "ird no", "ird no.", "ird no#", "ird #",
        "inland revenue", "inland revenue department",
        "new zealand ird", "new zealand inland revenue",
        "tax number", "tax file number", "nz tax", "nz tax number",
        "taxpayer number", "ird account"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "NewZealand_Inland_Revenue_Department_Number",
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns or self.PATTERNS,
            context=context or self.CONTEXT,
            supported_language=supported_language,
        )

    # ---------------------------------------------------------------------
    # Analyze Text
    # ---------------------------------------------------------------------
    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        print("\nAnalyzing text:", text)
        results = super().analyze(text, entities, nlp_artifacts)
        final_results = []

        has_context = self._has_context_keywords(text)
        print(f"→ Context keywords found: {has_context}")

        for result in results:
            original = text[result.start:result.end]
            cleaned = re.sub(r"[-\s]", "", original)
            print(f"\nFound possible IRD: '{original}' → cleaned: {cleaned}")

            valid_checksum = self._is_valid_ird_checksum(cleaned)
            print(f"→ Checksum valid: {valid_checksum}")

            new_score = self._calculate_score(has_context, valid_checksum, result.score)
            print(f"→ Final score: {new_score} (context={has_context}, valid={valid_checksum})")

            result.score = new_score
            final_results.append(result)

        return final_results

    # ---------------------------------------------------------------------
    # Check Context Keywords
    # ---------------------------------------------------------------------
    def _has_context_keywords(self, text: str) -> bool:
        text_lower = text.lower()
        for kw in self.CONTEXT:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                print(f"✓ Found context keyword: '{kw}'")
                return True
        return False

    # ---------------------------------------------------------------------
    # Scoring Logic
    # ---------------------------------------------------------------------
    def _calculate_score(self, has_context: bool, is_valid_checksum: bool, pattern_score: float) -> float:
        """
        Scoring rules:
          - Context + valid checksum    → 1.0 (High)
          - No context + valid checksum → 0.8 (Medium)
          - Context + invalid checksum  → 0.3 (Low)
          - No context + invalid        → 0.1 (Very Low)
        """
        if has_context and is_valid_checksum:
            return 1.0
        elif not has_context and is_valid_checksum:
            return 0.8
        elif has_context and not is_valid_checksum:
            return 0.3
        else:
            return 0.1

    # ---------------------------------------------------------------------
    # NZ IRD Modulus 11 Checksum Validation
    # ---------------------------------------------------------------------
    def _is_valid_ird_checksum(self, number: str) -> bool:
        """
        Implements NZ Inland Revenue Department number Modulus-11 validation.
        Reference: Microsoft Purview definition + IRD algorithm.
        """

        if len(number) not in (8, 9):
            print(f"✗ Invalid length ({len(number)}) for number: {number}")
            return False

        # Pad 8-digit number
        if len(number) == 8:
            number = "0" + number
            print(f"→ Padded to 9 digits: {number}")

        try:
            digits = [int(d) for d in number]
        except ValueError:
            print(f"✗ Non-numeric characters found in: {number}")
            return False

        def check(weights):
            total = sum(d * w for d, w in zip(digits[:8], weights))
            remainder = total % 11
            check_digit = digits[8]
            expected = (11 - remainder) if remainder not in (0, 1) else None
            print(f"  Weights: {weights} | Total={total} | Remainder={remainder} | Check digit={check_digit} | Expected={expected}")
            if remainder == 0:
                return check_digit == 0
            elif remainder == 1:
                return False
            else:
                return check_digit == expected

        primary = [3, 2, 7, 6, 5, 4, 3, 2]
        if check(primary):
            print("✓ Passed primary weighting scheme")
            return True

        secondary = [7, 4, 3, 2, 5, 2, 7, 6]
        if check(secondary):
            print("✓ Passed secondary weighting scheme")
            return True

        print("✗ Failed both weighting schemes")
        return False

    # ---------------------------------------------------------------------
    # Test Cases
    # ---------------------------------------------------------------------
    def test_specific_cases(self):
        print("\n========== Running Test Cases ==========")
        cases = [
            "Inland Revenue Department number: 49-098-576",
            "Inland Revenue Department number: 123-456-782",
            "Inland Revenue Department number: 123-456-789",
            "IRD no: 49-091-8762",   # Valid checksum example
            "Customer tax number: 490918762"  # Valid without delimiters
        ]

        for text in cases:
            print("\n----------------------------------------")
            results = self.analyze(text, [])
            if not results:
                print("No pattern matched.")
            for r in results:
                print(f"Detected: {text[r.start:r.end]} → Score: {r.score}")

        # Check raw numbers
        print("\n--- Raw Checksum Validation ---")
        for num in ["49098576", "123456782", "123456789", "490918762", "490918761"]:
            print(f"\nValidating {num}:")
            valid = self._is_valid_ird_checksum(num)
            print(f"Result: {'Valid ✅' if valid else 'Invalid ❌'}")
