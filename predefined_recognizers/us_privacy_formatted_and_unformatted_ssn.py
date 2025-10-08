from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
from typing import List, Optional
import re


class SSN_Formatted_Unformatted_Recognizer(PatternRecognizer):
    """
    Recognizer to detect and validate US Social Security Numbers (SSNs)
    with SSA rules, heuristics, and custom scoring + debug reason tagging.
    """

    PATTERNS = [
        Pattern(
            name="SSN formatted with hyphen",
            regex=r"\b\d{3}-\d{2}-\d{4}\b",
            score=0.85,
        ),
        Pattern(
            name="SSN formatted with spaces",
            regex=r"\b\d{3} \d{2} \d{4}\b",
            score=0.85,
        ),
        Pattern(
            name="SSN unformatted",
            regex=r"\b\d{9}\b",
            score=0.5,
        ),
    ]

    CONTEXT = [
        "social security number",
        "ssa number", 
        "social security",
        "ssn",
        "ssn#",
        "social security#",
        "security number",
        "ss number",
        "ssn no",
        "social security no",
        "ssn id",
        "social security id",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_formatted_unformatted_SSN",
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        results = super().analyze(text, entities, nlp_artifacts)
        
        print(f"=== DEBUG ANALYSIS ===")
        print(f"Text: '{text}'")
        print(f"Initial results: {len(results)}")

        for i, result in enumerate(results):
            pattern_text = text[result.start:result.end]
            has_context = self._has_context(text, result.start, result.end)
            validity = self._check_validity(pattern_text)

            # Debug print
            print(f"Result {i}:")
            print(f"  Pattern text: '{pattern_text}'")
            print(f"  Start/End: {result.start}/{result.end}")
            print(f"  Has context: {has_context}")
            print(f"  Validity: {validity}")
            print(f"  Original score: {result.score}")

            # --- NEW SCORING SYSTEM ---
            if has_context and validity == "valid":
                # keywords + correct SSNs: score > 0.8 or 1.0
                result.score = 0.9
                debug_reason = "keywords+valid"
            elif not has_context and validity == "valid":
                # no keywords + correct SSNs: score > 0.7
                result.score = 0.8
                debug_reason = "no_keywords+valid"
            elif has_context and validity == "suspicious":
                # keywords + incorrect SSNs: score < 0.7
                result.score = 0.6
                debug_reason = "keywords+suspicious"
            elif not has_context and validity == "suspicious":
                # no keywords + incorrect SSNs: score even lower
                result.score = 0.5
                debug_reason = "no_keywords+suspicious"
            elif has_context and validity == "invalid":
                # keywords + incorrect SSNs: score < 0.7
                result.score = 0.4
                debug_reason = "keywords+invalid"
            else:
                # no keywords + incorrect SSNs: score even lower
                result.score = 0.3
                debug_reason = "no_keywords+invalid"

            print(f"  Final score: {result.score}")
            print(f"  Debug reason: {debug_reason}")

            # Add metadata for debugging / logging
            result.recognition_metadata = {
                "validity": validity,
                "has_context": has_context,
                "debug_reason": debug_reason,
                "pattern_name": self._get_pattern_name(pattern_text),
            }

        results = [r for r in results if r.score > 0.3]
        print(f"Final results after filtering: {len(results)}")
        print("=== END DEBUG ===")
        return results

    def _has_context(self, text: str, start: int, end: int) -> bool:
        """
        Check for context words in the entire text with proximity weighting.
        """
        # Check entire text for context words (most reliable approach)
        text_lower = text.lower()
        
        # Check for exact context matches
        for context_word in self.CONTEXT:
            if context_word in text_lower:
                print(f"  Context found: '{context_word}' in text")
                return True
        
        return False

    def _get_pattern_name(self, pattern_text: str) -> str:
        """Determine which pattern matched the text."""
        if re.match(r"\b\d{3}-\d{2}-\d{4}\b", pattern_text):
            return "SSN formatted with hyphen"
        elif re.match(r"\b\d{3} \d{2} \d{4}\b", pattern_text):
            return "SSN formatted with spaces"
        elif re.match(r"\b\d{9}\b", pattern_text):
            return "SSN unformatted"
        else:
            return "unknown"

    def _check_validity(self, pattern_text: str) -> str:
        """
        Validate SSNs using SSA rules + heuristic realism checks.
        Returns: "valid", "suspicious", or "invalid".
        """
        # Extract only digits
        only_digits = "".join(c for c in pattern_text if c.isdigit())
        if len(only_digits) != 9:
            return "invalid"

        area, group, serial = only_digits[:3], only_digits[3:5], only_digits[5:]

        print(f"  SSN parts - Area: {area}, Group: {group}, Serial: {serial}")

        # --- SSA invalid combinations ---
        if (
            area == "000" or
            group == "00" or
            serial == "0000" or
            area == "666" or
            area.startswith("9")
        ):
            print(f"  Invalid: Failed SSA rules")
            return "invalid"

        # --- Known fake/test/demo SSNs ---
        known_invalids = {
            "123456789", "078051120", "111111111", "999999999", 
            "000000000", "123123123", "456456456", "789789789",
            "012345678", "987654321", "111223333", "222334444",
            "333445555", "444556666", "555667777", "666778888",
            "777889999", "888990000", "999001111"
        }
        if only_digits in known_invalids:
            print(f"  Invalid: Known fake/test SSN")
            return "invalid"

        # --- Heuristic checks for suspicious patterns ---
        # All same digit
        if len(set(only_digits)) == 1:
            print(f"  Suspicious: All digits are the same")
            return "suspicious"
            
        # Very few unique digits (more than 6 repeated digits)
        if len(set(only_digits)) <= 2:
            print(f"  Suspicious: Too few unique digits")
            return "suspicious"

        # Check for obvious sequential patterns (entire number)
        asc_seq = "0123456789"
        desc_seq = asc_seq[::-1]
        if only_digits in asc_seq or only_digits in desc_seq:
            print(f"  Suspicious: Entire number is sequential")
            return "suspicious"

        # Check for long sequential patterns (7+ consecutive sequential digits)
        for i in range(3):  # Check for sequences of 7 digits
            substring = only_digits[i:i+7]
            if len(substring) == 7 and (substring in asc_seq or substring in desc_seq):
                print(f"  Suspicious: Very long sequential substring '{substring}'")
                return "suspicious"

        # Check for repeated patterns (like 123123123)
        if len(only_digits) == 9:
            # Check for repeated 3-digit patterns
            if only_digits[:3] == only_digits[3:6] == only_digits[6:9]:
                print(f"  Suspicious: Repeated 3-digit pattern")
                return "suspicious"

        # --- Valid SSN range check ---
        area_num = int(area)
        if not (1 <= area_num <= 665 or 667 <= area_num <= 899):
            print(f"  Invalid: Area number {area_num} out of valid range")
            return "invalid"

        print(f"  Valid: Passed all checks")
        return "valid"
