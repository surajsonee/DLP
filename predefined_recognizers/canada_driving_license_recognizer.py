from typing import Optional, List
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
import re


class CanadaDriversLicenceRecognizer(PatternRecognizer):
    """
    Recognizes Canadian Driver’s Licence Numbers for all provinces.
    Enhanced to:
      - Prevent matches with trailing special characters like '&' or '_'
      - Avoid IBAN/other number overlaps
      - Use safer and stricter regex patterns
    """

    PATTERNS = [
        # --- Generic weak patterns ---
        Pattern(
            "Province name followed by 8 digits (weak)",
            r"\b([A-Za-z]+)\s+([0-9]{8})(?![A-Za-z0-9])",
            0.4,
        ),
        Pattern(
            "8 digits followed by 'license number' (moderate)",
            r"\b([0-9]{8})\s+(license number)\b",
            0.85,
        ),
        Pattern(
            "8 digits + province abbreviation + 'license number' (strong)",
            r"\b([0-9]{8})\s+(sk|ab|bc|mb|nb|nl|ns|nt|nu|on|pe|qc|yt)\s+(license number)\b",
            1.0,
        ),
        Pattern(
            "8 digits + full province name + 'license number' (strong)",
            r"\b([0-9]{8})\s+(Saskatchewan|Alberta|British Columbia|Manitoba|Newfoundland(?: and Labrador)?|Nova Scotia|Ontario|Quebec|Yukon)\s+(license number)\b",
            1.0,
        ),
        Pattern(
            "Contains 'license' and province with 8-digit number (strong)",
            r"(?=.*\b(license|license number)\b)(?=.*\b(Saskatchewan|Alberta|British Columbia|Manitoba|Newfoundland(?: and Labrador)?|Nova Scotia|Ontario|Quebec|Yukon|Northwest Territories|Nunavut|Prince Edward Island|New Brunswick|SK|AB|BC|MB|NL|NS|NT|NU|ON|PE|QC|YT)\b)(?=.*\b\d{8}\b)",
            1.0,
        ),
        # 8 digits only (generic weak pattern)
        Pattern(
            "8 digits only (weak)",
            r"(?<![A-Z]{2}\d{2}[A-Z]{4})\b(\d{8})(?![A-Za-z0-9])",
            0.1,
        ),

        # --- Province-specific patterns ---
        # Quebec (1 letter + 12 digits)
        Pattern(
            "Quebec Licence Number",
            r"\b([A-Z]\d{12})(?![A-Za-z0-9&])",
            0.9,
        ),
        Pattern(
            "Quebec Licence with Province",
            r"\b((Quebec|QC)\s*[A-Z]\d{12}|[A-Z]\d{12}\s*(Quebec|QC))(?![A-Za-z0-9&])",
            0.95,
        ),

        # PEI: 5–6 digits
        Pattern(
            "PEI Licence (weak)",
            r"\b(\d{5,6})(?![A-Za-z0-9])",
            0.25,
        ),
        Pattern(
            "PEI Licence with Province",
            r"\b((Prince\sEdward\sIsland|PE|PEI)\s*\d{5,6}|\d{5,6}\s*(Prince\sEdward\sIsland|PE|PEI))(?![A-Za-z0-9])",
            0.9,
        ),

        # Ontario (1 letter + 14 digits, often hyphenated)
        Pattern(
            "Ontario Licence",
            r"\b(?:Ontario|ON)?\s*(?:license number|license|DL|Driving license number)?\s*([A-Z]\d{4}-?\d{5}-?\d{5})(?![A-Za-z0-9])",
            0.95,
        ),

        # Nova Scotia (14 digits)
        Pattern(
            "Nova Scotia Licence",
            r"\b(?:Nova\sScotia|NS)\s*(?:license\snumber|DL|license|Driving\slicense\snumber)?\s*(\d{14})(?![A-Za-z0-9])",
            0.95,
        ),

        # Newfoundland and Labrador (1 letter + 12 digits)
        Pattern(
            "Newfoundland and Labrador Licence",
            r"\b(?:Newfoundland(?: and Labrador)?|NL)\s*(?:license|DL|Driving\slicense\snumber)?\s*([A-Z]\d{12})(?![A-Za-z0-9])",
            0.95,
        ),

        # New Brunswick (1 letter + 14 digits)
        Pattern(
            "New Brunswick Licence",
            r"\b(?:New\sBrunswick|NB)\s*(?:license\snumber|DL|license|Driving\slicense\snumber)?\s*([A-Z]\d{14})(?![A-Za-z0-9])",
            0.95,
        ),

        # Manitoba (15 digits)
        Pattern(
            "Manitoba Licence",
            r"\b(?:Manitoba|MB)\s*(?:license number|DL|license|Driving\slicense\snumber)?\s*(\d{15})(?![A-Za-z0-9])",
            0.95,
        ),

        # British Columbia (1 letter + 7 digits)
        Pattern(
            "British Columbia Licence",
            r"\b(?:British\sColumbia|BC)\s*(?:license\snumber|DL|license|Driving\slicense\snumber)?\s*([A-Z]\d{7})(?![A-Za-z0-9])",
            0.95,
        ),

        # Alberta (7–9 digits, sometimes with hyphen)
        Pattern(
            "Alberta Licence",
            r"\b(?:Alberta|AB)\s*(?:license number|DL|license|Driving license number)?\s*(\d{5,9}|\d{6}-\d{3})(?![A-Za-z0-9])",
            0.95,
        ),

        # Saskatchewan (9 digits)
        Pattern(
            "Saskatchewan Licence",
            r"\b(?:Saskatchewan|SK)\s*(?:license number|DL|license|Driving license number)?\s*(\d{9})(?![A-Za-z0-9])",
            0.95,
        ),

        # Yukon (6 digits)
        Pattern(
            "Yukon Licence",
            r"\b(?:Yukon|YT)\s*(?:license number|DL|license|Driving license number)?\s*(\d{6})(?![A-Za-z0-9])",
            0.9,
        ),

        # NWT/Nunavut (6 digits)
        Pattern(
            "Northwest Territories / Nunavut Licence",
            r"\b(?:Northwest\sTerritories|NWT|Nunavut|NU)\s*(?:license number|DL|license|Driving license number)?\s*(\d{6})(?![A-Za-z0-9])",
            0.9,
        ),
    ]

    CONTEXT = [
        "driver",
        "license",
        "permit",
        "identification",
        "province",
        "canadian",
        "driving license number",
        "DL",
        "driver's license",
        "driving permit",
        "provincial",
        "license number",
        "DLN",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CANADA_DRIVERS_LICENCE",
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            supported_language=supported_language,
            patterns=patterns,
            context=context,
        )

    def analyze(
        self, text: str, entities: Optional[List[str]] = None, nlp_artifacts=None
    ) -> List[RecognizerResult]:
        """Exclude IBAN-like matches and filter clean results."""
        results = super().analyze(text, entities, nlp_artifacts)
        IBAN_REGEX = r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b"
        iban_spans = [(m.start(), m.end()) for m in re.finditer(IBAN_REGEX, text)]

        filtered_results = []
        for r in results:
            if not any(start <= r.start and r.end <= end for start, end in iban_spans):
                filtered_results.append(r)
            else:
                print(f"Excluded IBAN-like match: '{text[r.start:r.end]}'")
        return filtered_results

