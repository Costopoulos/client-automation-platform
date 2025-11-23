from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List

from app.models.extraction import ValidationWarning


class BaseParser(ABC):
    """Abstract base class for all document parsers"""

    @abstractmethod
    def parse(self, filepath: Path) -> Dict:
        """
        Parse file and return structured data

        Args:
            filepath: Path to the file to parse

        Returns:
            Dictionary containing extracted data
        """
        pass

    @abstractmethod
    def validate(self, data: Dict) -> List[ValidationWarning]:
        """
        Validate extracted data and return warnings

        Args:
            data: Dictionary of extracted data

        Returns:
            List of validation warnings
        """
        pass
