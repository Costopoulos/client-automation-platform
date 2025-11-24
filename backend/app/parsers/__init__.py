"""
Parsers module for document extraction

Structure:
- base.py, utils.py: Core utilities
- rule_based/: Traditional BeautifulSoup/regex parsers
- llm_based/: AI-powered extraction using OpenAI
- hybrid/: LLM-first with rule-based fallback (recommended)
"""

from .base import BaseParser
from .hybrid.email_parser import HybridEmailParser
from .hybrid.form_parser import HybridFormParser
from .hybrid.invoice_parser import HybridInvoiceParser
from .rule_based.email_parser import RuleBasedEmailParser
from .rule_based.form_parser import RuleBasedFormParser
from .rule_based.invoice_parser import RuleBasedInvoiceParser

# Default exports: Hybrid parsers (LLM-first with fallback)
FormParser = HybridFormParser
EmailParser = HybridEmailParser
InvoiceParser = HybridInvoiceParser

__all__ = [
    "BaseParser",
    # Hybrid parsers (recommended, default)
    "HybridFormParser",
    "HybridEmailParser",
    "HybridInvoiceParser",
    # Convenience aliases
    "FormParser",
    "EmailParser",
    "InvoiceParser",
    # Rule-based parsers (explicit access)
    "RuleBasedFormParser",
    "RuleBasedEmailParser",
    "RuleBasedInvoiceParser",
]
