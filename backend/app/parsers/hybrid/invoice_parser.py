import time
from pathlib import Path
from typing import Dict, List

import structlog

from app.config import get_settings
from app.models.extraction import ValidationWarning
from app.parsers.base import BaseParser
from app.parsers.llm_based.invoice_parser import LLMInvoiceParser
from app.parsers.rule_based.invoice_parser import RuleBasedInvoiceParser

logger = structlog.get_logger()


class HybridInvoiceParser(BaseParser):
    """
    Hybrid invoice parser that tries LLM extraction first, falls back to rule-based

    Strategy:
    1. Try LLM extraction if enabled
    2. Check confidence threshold
    3. Fall back to rule-based if confidence too low or LLM fails
    4. Track which method was used
    """

    def __init__(self):
        """Initialize both LLM and rule-based parsers"""
        self.settings = get_settings()
        self.llm_parser = None
        self.rule_parser = RuleBasedInvoiceParser()

        # Only initialize LLM parser if enabled
        if self.settings.use_llm_extraction:
            try:
                self.llm_parser = LLMInvoiceParser()
            except Exception as e:
                logger.warning(
                    "llm_parser_init_failed",
                    error=str(e),
                    fallback="rule-based only",
                )

    def parse(self, filepath: Path) -> Dict:
        """
        Parse invoice using hybrid strategy

        Args:
            filepath: Path to HTML invoice file

        Returns:
            Dictionary with extracted fields and metadata
        """
        start_time = time.time()

        # Try LLM extraction first if enabled
        if self.settings.use_llm_extraction and self.llm_parser:
            try:
                data = self._try_llm_extraction(filepath)
                if data:
                    duration = (time.time() - start_time) * 1000
                    logger.info(
                        "hybrid_parse_completed",
                        method=data.get("_extraction_method"),
                        confidence=data.get("_confidence"),
                        duration_ms=round(duration, 2),
                        filepath=str(filepath),
                    )
                    return data
            except Exception as e:
                logger.warning(
                    "llm_extraction_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    fallback="rule-based",
                    filepath=str(filepath),
                )

        # Fall back to rule-based extraction
        data = self.rule_parser.parse(filepath)
        data["_extraction_method"] = "rule-based"
        data["_confidence"] = None

        duration = (time.time() - start_time) * 1000
        logger.info(
            "hybrid_parse_completed",
            method="rule-based",
            duration_ms=round(duration, 2),
            filepath=str(filepath),
        )

        return data

    def _try_llm_extraction(self, filepath: Path) -> Dict | None:
        """
        Attempt LLM extraction with confidence checking

        Args:
            filepath: Path to file

        Returns:
            Extracted data if successful and confident, None otherwise
        """
        data = self.llm_parser.parse(filepath)
        confidence = data.get("_confidence", 0.0)

        # Check if confidence meets threshold
        if confidence >= self.settings.llm_confidence_threshold:
            data["_extraction_method"] = "llm"
            logger.info(
                "llm_extraction_success",
                confidence=confidence,
                threshold=self.settings.llm_confidence_threshold,
            )
            return data

        # Low confidence
        if self.settings.llm_fallback_to_rules:
            logger.warning(
                "llm_confidence_too_low",
                confidence=confidence,
                threshold=self.settings.llm_confidence_threshold,
                fallback="rule-based",
            )
            return None
        else:
            # Use LLM result anyway if fallback disabled
            data["_extraction_method"] = "llm-low-confidence"
            logger.warning(
                "llm_low_confidence_used",
                confidence=confidence,
                reason="fallback disabled",
            )
            return data

    def validate(self, data: Dict) -> List[ValidationWarning]:
        """
        Validate extracted data using appropriate validator

        Args:
            data: Dictionary of extracted data

        Returns:
            List of validation warnings
        """
        extraction_method = data.get("_extraction_method", "rule-based")

        if extraction_method.startswith("llm") and self.llm_parser:
            return self.llm_parser.validate(data)
        else:
            return self.rule_parser.validate(data)
