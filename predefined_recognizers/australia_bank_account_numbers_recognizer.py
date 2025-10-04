from typing import Optional, List, Set
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
import requests
import re

class AustraliaBankAccountRecognizer(PatternRecognizer):
    """
    Recognizes Australian Bank Account Numbers with BSB validation, including:
    - BSB + Account with dashes/spaces: 012-003 1234567890, 012 003-1234567890
    - Account + BSB with dashes/spaces: 1234567890-012-003, 1234567890 012 003
    Excludes no-separator formats like 0120031234567890
    Uses live BSB data from Australian Payments Network and static validation.
    """

    # Official BSB directory from Australian Payments Network
    BSB_DIRECTORY_URL = "https://bsb.auspaynet.com.au/Public/CS4BSBDir.nsf/spdate/651A09906737C1A9CA258CB900527726/$file/BSBDirectoryJun25-351.txt"

    # Static BSBs stored as 6-digit strings
    STATIC_BSB_NUMBERS = {
        "012002", "012003", "012004", "012005", "012006", "012009", "012010",
        "012012", "012013", "012016", "012017", "012019", "012020", "012023",
        "012028", "012030", "012033", "012037", "012040", "012043"
    }

    # Patterns to handle all cases with separators
    PATTERNS = [
        Pattern(
            "Australia Bank Account (Flexible)",
            r"\b\d{3}[- ]\d{3}[- ]\d{6,10}\b",  # BSB + Account
            0.7,
        ),
        Pattern(
            "Australia Bank Account (Reverse)",
            r"\b\d{6,10}[- ]\d{3}[- ]\d{3}\b",  # Account + BSB
            0.7,
        )
    ]

    CONTEXT = [
        "bank account", "bsb", "account number", "bsb code", "bank details",
        "banking information", "billing account", "account holder", "account-no",
        "bank account number", "bsb/bank code", "financial institution",
        "fund transfers", "branch code", "account info",
    ]

    NEGATIVE_CONTEXT = [
        "driver", "license", "licence", "permit", "identification",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "AUSTRALIA_BANK_ACCOUNT",
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )
        self.known_bsb_numbers = self._load_bsb_directory()
        self.known_bsb_numbers.update(self.STATIC_BSB_NUMBERS)

    def _load_bsb_directory(self) -> Set[str]:
        """Fetch and parse current BSB directory from Australian Payments Network"""
        try:
            response = requests.get(self.BSB_DIRECTORY_URL, timeout=5)
            response.raise_for_status()
            bsb_set = set()
            for line in response.text.splitlines():
                if len(line) >= 6 and line[:6].isdigit():
                    bsb_set.add(line[:6])  # Store as 6-digit string
            return bsb_set
        except requests.RequestException:
            # Return empty set if network issue
            return set()

    def analyze(self, text: str, entities: Optional[List[str]] = None, nlp_artifacts=None) -> List[RecognizerResult]:
        results = super().analyze(text, entities, nlp_artifacts)
        updated_results = []
        lower_text = text.lower()

        # Check context presence once for the whole text
        has_positive_context = any(ctx in lower_text for ctx in self.CONTEXT)
        has_negative_context = any(neg in lower_text for neg in self.NEGATIVE_CONTEXT)

        for result in results:
            snippet = text[result.start:result.end]
            
            # Split into parts using separators
            parts = re.split(r'[- ]+', snippet)
            
            # We should have exactly 3 parts
            if len(parts) != 3:
                continue
                
            # Determine order based on part lengths
            if len(parts[0]) == 3 and len(parts[1]) == 3 and 6 <= len(parts[2]) <= 10:
                # BSB + Account format
                bsb_digits = parts[0] + parts[1]
                account_digits = parts[2]
            elif len(parts[0]) in range(6, 11) and len(parts[1]) == 3 and len(parts[2]) == 3:
                # Account + BSB format
                bsb_digits = parts[1] + parts[2]
                account_digits = parts[0]
            else:
                continue  # Doesn't match expected lengths
                
            # Validate account number length
            if not (6 <= len(account_digits) <= 10):
                continue

            # Apply scoring based on validation and context
            if bsb_digits in self.known_bsb_numbers:
                if has_positive_context:
                    result.score = 1.0  # Known BSB + context
                else:
                    result.score = 0.85  # Known BSB without context
            else:
                if has_positive_context:
                    result.score = 0.75  # Valid pattern + context
                else:
                    result.score = 0.6   # Valid pattern without context

            # Apply negative context penalty
            if has_negative_context:
                result.score *= 0.15

            if result.score > 0.3:
                updated_results.append(result)

        return updated_results
