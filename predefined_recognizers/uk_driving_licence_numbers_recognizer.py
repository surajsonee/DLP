from presidio_analyzer import PatternRecognizer, Pattern
import re
from typing import List, Optional

class UKDriversLicenseRecognizer(PatternRecognizer):
    # Define patterns for UK Driver's License numbers
    PATTERNS = [
        Pattern(
            "UK Driver License Pattern", 
            r"\b[A-Za-z9]{5}\d(0[1-9]|1[0-2]|5[1-9]|6[0-2])([0][1-9]|[12]\d|3[01])\d[A-Za-z9]{2}\d{5}\b", 
            0.7  # Initial confidence score for pattern match
        )
    ]
    
    # Context keywords related to UK driving licenses
    CONTEXT = [
        "driver's licence", "driving licence", "licence number", "UK license", "UK driving licence", "DVLA"
    ]

    def __init__(self, supported_language: Optional[str] = None):
        super().__init__(
            supported_entity="UK_DRIVERS_LICENSE",
            supported_language=supported_language,
            patterns=self.PATTERNS,
            context=self.CONTEXT
        )

    def enhance_confidence(self, text, pattern_result):
        """
        Enhance confidence based on proximity to UK-specific keywords.
        """
        context_window = 50  # Check within 50 characters before and after
        start, end = pattern_result.start, pattern_result.end
        surrounding_text = text[max(0, start - context_window):min(len(text), end + context_window)].lower()

        # Check for keywords in proximity
        keyword_present = any(keyword.lower() in surrounding_text for keyword in self.CONTEXT)

        # Adjust confidence levels based on the proximity of keywords
        if keyword_present:
            pattern_result.score = min(pattern_result.score + 0.3, 1.0)  # Increase the score, cap at 1.0
        else:
            pattern_result.score = pattern_result.score * 0.8  # Slightly reduce confidence if no context is found

        return pattern_result

    def analyze(self, text, entities, nlp_artifacts=None):
        """
        Override the analyze method to enhance results with contextual information.
        """
        results = super().analyze(text, entities, nlp_artifacts)
        enhanced_results = [self.enhance_confidence(text, result) for result in results]
        return enhanced_results