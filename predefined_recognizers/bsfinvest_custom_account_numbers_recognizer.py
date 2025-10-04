import re
from typing import Optional, List
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
import logging

logger = logging.getLogger("presidio-analyzer")

class BFSInvestCustomAccountRecognizer(PatternRecognizer):
    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "BFSInvest_CUSTOM_ACCOUNT",
        account_list_file: str = "/usr/share/data/bgf_custom_acc.txt",
        enable_case_insensitivity: bool = True
    ):
        # Load account numbers with error handling
        self.account_numbers = self._load_account_numbers(account_list_file)
        if not self.account_numbers:
            logger.warning(f"No valid account numbers loaded from {account_list_file}")
        
        # Build regex pattern with performance optimizations
        account_pattern = "|".join(re.escape(acc) for acc in self.account_numbers)
        flags = re.IGNORECASE if enable_case_insensitivity else 0
        
        # Enhanced pattern with context awareness
        base_pattern = rf"""
            \b(?:account|id|bfsinvest)[\s:#-]*  # Contextual prefix
            ({account_pattern})                  # Capture group for account number
            \b                                  # Word boundary
        """
        pattern = Pattern(
            name="BFSInvest_CUSTOM_ACCOUNT",
            regex=re.compile(base_pattern, re.VERBOSE | flags),
            score=0.85,  # Lower confidence to allow overrides
        )

        # Define contextual triggers
        context = context or ["account", "id", "bfsinvest", "custom acc"]
        
        super().__init__(
            supported_entity=supported_entity,
            patterns=[pattern],
            context=context,
            supported_language=supported_language,
        )

    def _load_account_numbers(self, file_path: str) -> List[str]:
        """Load and validate account numbers with error resilience"""
        try:
            with open(file_path, 'r') as file:
                return [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            logger.error(f"Account list file not found: {file_path}")
            return []
        except Exception as e:
            logger.exception(f"Critical error loading accounts: {str(e)}")
            return []

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts=None
    ) -> List[RecognizerResult]:
        """Enhanced analysis with validation and large-list handling"""
        # Short-circuit if no account numbers loaded
        if not self.account_numbers:
            logger.debug("Skipping analysis - no account numbers available")
            return []

        # Performance optimization for large lists
        if len(self.account_numbers) > 1000:
            return self._analyze_large_list(text)
            
        return super().analyze(text, entities, nlp_artifacts)

    def _analyze_large_list(self, text: str) -> List[RecognizerResult]:
        """Efficient scanning for large account lists using set lookups"""
        results = []
        words = re.split(r'\s+', text)  # Simple tokenization
        
        # Create normalized account set (case-insensitive if enabled)
        account_set = {acc.lower() for acc in self.account_numbers} 
        
        for word in words:
            # Strip surrounding punctuation
            clean_word = re.sub(r'^\W+|\W+$', '', word)
            if not clean_word:
                continue
                
            # Case-normalized comparison
            candidate = clean_word.lower() if self.patterns[0].regex.flags & re.IGNORECASE else clean_word
            
            if candidate in account_set:
                # Validate original casing if case-sensitive
                if not self.patterns[0].regex.flags & re.IGNORECASE and clean_word not in self.account_numbers:
                    continue
                    
                # Position calculation
                start = text.index(clean_word)
                end = start + len(clean_word)
                results.append(
                    RecognizerResult(
                        entity_type=self.supported_entity,
                        start=start,
                        end=end,
                        score=self.patterns[0].score,
                        analysis_explanation=f"Matched account: {clean_word}"
                    )
                )
        return results

    def validate_result(self, pattern_text: str) -> bool:
        """Post-match validation against source list"""
        # Normalize to case-insensitive comparison if enabled
        if self.patterns[0].regex.flags & re.IGNORECASE:
            return any(pattern_text.lower() == acc.lower() for acc in self.account_numbers)
        return pattern_text in self.account_numbers
