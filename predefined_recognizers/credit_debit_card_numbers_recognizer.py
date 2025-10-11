import re
import logging
from typing import Optional, List
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult

logger = logging.getLogger("presidio-analyzer")
logger.setLevel(logging.DEBUG)


class DatotelCreditDebitCardRecognizer(PatternRecognizer):
    logger.info("Initializing Datotel Custom Credit/Debit Card & SSN Recognizer...")

    # Credit/Debit Card Patterns
    CARD_PATTERNS = [
        Pattern("Credit/Debit Card - Formatted", r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", 0.5),
        Pattern("Credit/Debit Card - Unformatted", r"\b\d{16}\b", 0.5),
        Pattern("Amex Card - Formatted", r"\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b", 0.5),
        Pattern("Amex Card - Unformatted", r"\b3[47]\d{13}\b", 0.5),
    ]

    # SSN Patterns - STRICTER patterns that require exactly 3-2-4 digits
    SSN_PATTERNS = [
        Pattern("SSN formatted with hyphen", r"\b\d{3}-\d{2}-\d{4}\b", 0.85),
        Pattern("SSN formatted with spaces", r"\b\d{3} \d{2} \d{4}\b", 0.85),
        Pattern("SSN unformatted", r"\b\d{9}\b", 0.5),
    ]

    # Combined patterns for both entities
    PATTERNS = CARD_PATTERNS + SSN_PATTERNS

    # Combined context terms
    CONTEXT_TERMS = [
        # Card context terms
        "credit", "debit", "card", "visa", "mastercard", "amex", "american express",
        "discover", "jcb", "diners club", "expiration", "expiry", "valid thru",
        "valid from", "cvv", "cvc", "cid", "security code", "card number",
        "cardholder", "card holder", "account number", "banking", "issuer", "csv",
        "expiry date", "card verification", "billing", "payment", "credit card",
        "debit card", "card type", "card details", "card information", "card issuer",
        "card network", "master card", "amex card", "visa card", "card security",
        "card expiry", "card expiration", "card verification value", "card verification code",
        # SSN context terms
        "social security number", "ssa number", "social security", "ssn", "ssn#",
        "social security#", "security number", "ss number", "ssn no", "social security no",
        "ssn id", "social security id", "ssnid"
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
    # Helper: Luhn check for credit cards
    # ----------------------------------------------------------------------
    @staticmethod
    def luhn_check(card_number: str) -> bool:
        # Remove non-digit characters
        digits_str = re.sub(r'\D', '', card_number)
        if not digits_str:
            return False
            
        digits = [int(d) for d in digits_str]
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
    # Helper: SSN validation - UPDATED WITH STRICT RULES
    # ----------------------------------------------------------------------
    def _check_ssn_validity(self, pattern_text: str) -> str:
        """
        Validate SSNs using strict SSA rules:
        1. First 3 digits: 001-899 excluding 666
        2. Middle 2 digits: 01-99 (not 00)
        3. Last 4 digits: 0001-9999 (not 0000)
        4. Cannot be all identical digits
        Returns: "valid", "suspicious", or "invalid".
        """
        # Extract only digits
        only_digits = "".join(c for c in pattern_text if c.isdigit())
        if len(only_digits) != 9:
            return "invalid"

        area, group, serial = only_digits[:3], only_digits[3:5], only_digits[5:]

        logger.debug(f"SSN parts - Area: {area}, Group: {group}, Serial: {serial}")

        # --- KNOWN INVALID/TEST SSNs ---
        known_invalid_ssns = {
            "123456789",  # Well-known test SSN
            "111111111", "222222222", "333333333", "444444444", "555555555",
            "666666666", "777777777", "888888888", "999999999", "000000000",
            "123454321", "112233445", "111223333", "123121234",
            "078051120",  # Woolworth's wallet SSN
            "219099999", "457555462"  # Other advertised SSNs
        }
        
        if only_digits in known_invalid_ssns:
            logger.debug(f"Invalid: Known test/fake SSN")
            return "invalid"

        # Rule 1: First 3 digits: 001-899 excluding 666
        area_num = int(area)
        if not (1 <= area_num <= 899) or area_num == 666:
            logger.debug(f"Invalid: Area number {area_num} not in range 001-899 or is 666")
            return "invalid"

        # Rule 2: Middle 2 digits: 01-99 (not 00)
        group_num = int(group)
        if not (1 <= group_num <= 99):
            logger.debug(f"Invalid: Group number {group_num} not in range 01-99")
            return "invalid"

        # Rule 3: Last 4 digits: 0001-9999 (not 0000)
        serial_num = int(serial)
        if not (1 <= serial_num <= 9999):
            logger.debug(f"Invalid: Serial number {serial_num} not in range 0001-9999")
            return "invalid"

        # Rule 4: Cannot be all identical digits
        if len(set(only_digits)) == 1:
            logger.debug(f"Invalid: All digits are identical")
            return "invalid"

        # --- Additional suspicious pattern checks ---
        # Consecutive sequences
        if only_digits in ["012345678", "123456789", "234567890", "345678901",
                        "456789012", "567890123", "678901234", "789012345",
                        "890123456", "901234567", "987654321", "876543210",
                        "765432109", "654321098", "543210987", "432109876",
                        "321098765", "210987654", "109876543"]:
            logger.debug(f"Invalid: Consecutive sequence pattern")
            return "invalid"

        # Repeated patterns
        if only_digits[:3] == only_digits[3:6] == only_digits[6:9]:
            logger.debug(f"Invalid: Repeated 3-digit pattern")
            return "invalid"

        # Very few unique digits
        if len(set(only_digits)) <= 3:
            logger.debug(f"Suspicious: Too few unique digits")
            return "suspicious"

        # Check for advertising/test SSN patterns
        if area in ["123", "111", "222", "333", "444", "555", "666", "777", "888", "999"]:
            if group in ["45", "11", "22", "33", "44", "55", "66", "77", "88", "99"]:
                if serial in ["6789", "1111", "2222", "3333", "4444", "5555", "6666", "7777", "8888", "9999"]:
                    logger.debug(f"Suspicious: Advertising/test SSN pattern")
                    return "suspicious"

        logger.debug(f"Valid: Passed all SSA validation rules")
        return "valid"

    # ----------------------------------------------------------------------
    # Helper: Check if text matches card patterns
    # ----------------------------------------------------------------------
    def _is_card_pattern(self, pattern_text: str) -> bool:
        """Check if the pattern matches any credit/debit card pattern"""
        card_patterns_to_check = [
            r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$",  # Standard 16-digit
            r"^\d{16}$",  # Unformatted 16-digit
            r"^3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}$",  # Amex formatted
            r"^3[47]\d{13}$"  # Amex unformatted
        ]
        
        for pattern in card_patterns_to_check:
            if re.match(pattern, pattern_text):
                return True
        return False

    # ----------------------------------------------------------------------
    # Helper: Check if text matches SSN patterns
    # ----------------------------------------------------------------------
    def _is_ssn_pattern(self, pattern_text: str) -> bool:
        """Check if the pattern matches any SSN pattern"""
        ssn_patterns_to_check = [
            r"^\d{3}-\d{2}-\d{4}$",  # SSN with hyphen (EXACT 3-2-4)
            r"^\d{3} \d{2} \d{4}$",  # SSN with spaces (EXACT 3-2-4)
            r"^\d{9}$"  # Unformatted SSN (EXACT 9 digits)
        ]
        
        for pattern in ssn_patterns_to_check:
            if re.match(pattern, pattern_text):
                return True
        return False

    # ----------------------------------------------------------------------
    # Main analysis
    # ----------------------------------------------------------------------
    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        logger.info(f"Analyzing text for Datotel Custom Credit/Debit Card & SSN: {text}")
        results = super().analyze(text, entities, nlp_artifacts)
        logger.info(f"Found {len(results)} potential card numbers or SSNs")

        if not results:
            return []

        # Check for context in the entire text
        has_context = bool(self.context_regex.search(text))
        logger.info(f"Context detected in text: {has_context}")

        # Process each result and collect validation info
        processed_results = []
        found_cards = []
        found_ssns = []
        
        for result in results:
            pattern_text = text[result.start:result.end]
            logger.debug(f"Processing: {pattern_text}")

            # Determine entity type and validate
            is_card = self._is_card_pattern(pattern_text)
            is_ssn = self._is_ssn_pattern(pattern_text)

            # Skip if it doesn't match our strict patterns
            if not (is_card or is_ssn):
                logger.debug(f"Skipping {pattern_text} - doesn't match strict patterns")
                continue

            if is_card:
                entity_type = "CARD"
                is_valid = self.luhn_check(pattern_text)
                logger.debug(f"Card validation: {'Valid' if is_valid else 'Invalid'}")
                found_cards.append({
                    'result': result,
                    'pattern_text': pattern_text,
                    'is_valid': is_valid
                })
            else:  # is_ssn
                entity_type = "SSN"
                validity_status = self._check_ssn_validity(pattern_text)
                is_valid = (validity_status == "valid")
                logger.debug(f"SSN validation: {validity_status}")
                found_ssns.append({
                    'result': result,
                    'pattern_text': pattern_text,
                    'is_valid': is_valid
                })

            # Store the processed result
            processed_results.append({
                'result': result,
                'pattern_text': pattern_text,
                'entity_type': entity_type,
                'is_valid': is_valid
            })

        # Determine the scenario based on your test cases
        has_any_card = len(found_cards) > 0
        has_any_ssn = len(found_ssns) > 0
        has_valid_card = any(card['is_valid'] for card in found_cards)
        has_valid_ssn = any(ssn['is_valid'] for ssn in found_ssns)
        
        logger.info(f"Scenario Analysis - Cards: {len(found_cards)}, SSNs: {len(found_ssns)}, Valid Card: {has_valid_card}, Valid SSN: {has_valid_ssn}, Context: {has_context}")

        # Determine which test case we have
        if has_any_card and has_any_ssn and has_valid_card and has_valid_ssn:
            # Case 1 & 5: Both present and valid
            scenario = "both_present_valid"
        elif has_any_card and not has_any_ssn:
            # Case 2: Only card present
            scenario = "only_card"
        elif has_any_ssn and not has_any_card:
            # Case 3: Only SSN present
            scenario = "only_ssn"
        elif has_any_card and has_any_ssn and (not has_valid_card or not has_valid_ssn):
            # Case 4: Both present but one invalid
            scenario = "both_present_one_invalid"
        else:
            scenario = "unknown"
            
        logger.info(f"Detected Scenario: {scenario}")

        # Now apply scoring based on the exact test cases
        final_results = []
        for processed in processed_results:
            result = processed['result']
            pattern_text = processed['pattern_text']
            entity_type = processed['entity_type']
            is_valid = processed['is_valid']

            # ---------------------------------------------------------------
            # EXACT Scoring logic based on your 5 test cases:
            # ---------------------------------------------------------------
            if scenario == "both_present_valid":
                # Case 1 & 5: keywords + Both present and valid → scores > 0.7
                if has_context and is_valid:
                    score = 0.9  # Keywords + correct number
                    debug_reason = "keywords_both_valid"
                elif not has_context and is_valid:
                    score = 0.75  # No keywords + correct number
                    debug_reason = "no_keywords_both_valid"
                else:
                    score = 0.6
                    debug_reason = "both_valid_but_entity_invalid"
                    
            elif scenario == "only_card":
                # Case 2: Only card present → scores < 0.7
                if has_context and is_valid:
                    score = 0.65  # Valid card but no SSN
                    debug_reason = "only_card_with_context"
                elif not has_context and is_valid:
                    score = 0.6  # Valid card but no SSN + no context
                    debug_reason = "only_card_no_context"
                else:
                    score = 0.5  # Invalid card
                    debug_reason = "only_card_invalid"
                    
            elif scenario == "only_ssn":
                # Case 3: Only SSN present → scores < 0.7
                if has_context and is_valid:
                    score = 0.65  # Valid SSN but no card
                    debug_reason = "only_ssn_with_context"
                elif not has_context and is_valid:
                    score = 0.6  # Valid SSN but no card + no context
                    debug_reason = "only_ssn_no_context"
                else:
                    score = 0.5  # Invalid SSN
                    debug_reason = "only_ssn_invalid"
                    
            elif scenario == "both_present_one_invalid":
                # Case 4: Both present but one invalid → scores < 0.7
                if has_context and is_valid:
                    score = 0.65  # Valid entity but partner is invalid
                    debug_reason = "both_present_one_invalid_with_context"
                elif not has_context and is_valid:
                    score = 0.6  # Valid entity but partner is invalid + no context
                    debug_reason = "both_present_one_invalid_no_context"
                else:
                    score = 0.5  # This entity is also invalid
                    debug_reason = "both_present_both_invalid"
            else:
                # Fallback
                score = 0.5
                debug_reason = "unknown_scenario"

            result.score = round(score, 2)
            
            # Add metadata for debugging
            result.recognition_metadata = {
                "entity_type": entity_type,
                "is_valid": is_valid,
                "has_context": has_context,
                "debug_reason": debug_reason,
                "pattern_text": pattern_text,
                "scenario": scenario,
                "cards_found": len(found_cards),
                "ssns_found": len(found_ssns),
                "has_valid_card": has_valid_card,
                "has_valid_ssn": has_valid_ssn
            }

            logger.info(f"FINAL SCORE - {entity_type}: {pattern_text} | Valid: {is_valid} | Scenario: {scenario} | Context: {has_context} | Score: {result.score}")
            final_results.append(result)

        return final_results
