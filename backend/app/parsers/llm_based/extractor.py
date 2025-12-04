import json
import time
from typing import Any, Dict, Tuple

import structlog
from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from app.config import get_settings
from app.models.extraction import RecordType

logger = structlog.get_logger()


class AIExtractor:
    """
    AI-powered extraction engine using OpenAI API

    Handles intelligent data extraction from unstructured documents
    with confidence scoring, retry logic, and error handling.
    """

    def __init__(self):
        """Initialize AI extractor with OpenAI client"""
        settings = get_settings()
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout,
        )
        self.model = settings.openai_model
        self.temperature = settings.openai_temperature
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay for exponential backoff

    def extract_structured_data(
        self,
        content: str,
        schema: Dict[str, str],
        document_type: RecordType,
    ) -> Tuple[Dict[str, Any], float]:
        """
        Extract structured data from document content using LLM

        Args:
            content: Raw document content (HTML, text, etc.)
            schema: Dictionary mapping field names to descriptions
            document_type: Type of document being processed

        Returns:
            Tuple of (extracted_data, confidence_score)
            - extracted_data: Dictionary with extracted field values
            - confidence_score: Overall confidence (0.0-1.0)

        Raises:
            Exception: If extraction fails after all retries
        """
        logger.info(
            "ai_extraction_started",
            document_type=document_type.value,
            field_count=len(schema),
        )

        # Build extraction prompt
        prompt = self._build_extraction_prompt(content, schema, document_type)

        # Attempt extraction with retry logic
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._call_llm(prompt)
                extracted_data = self._parse_llm_response(response)
                confidence = self._calculate_confidence(extracted_data, schema)

                logger.info(
                    "ai_extraction_succeeded",
                    document_type=document_type.value,
                    confidence=confidence,
                    attempt=attempt,
                )

                return extracted_data, confidence

            except RateLimitError as e:
                logger.warning(
                    "ai_rate_limit_error",
                    attempt=attempt,
                    max_retries=self.max_retries,
                    error=str(e),
                )
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                else:
                    raise Exception(f"Rate limit exceeded after {self.max_retries} attempts") from e

            except APITimeoutError as e:
                logger.warning(
                    "ai_timeout_error",
                    attempt=attempt,
                    max_retries=self.max_retries,
                    error=str(e),
                )
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                else:
                    raise Exception(f"API timeout after {self.max_retries} attempts") from e

            except APIError as e:
                logger.warning(
                    "ai_api_error",
                    attempt=attempt,
                    max_retries=self.max_retries,
                    error=str(e),
                )
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                else:
                    raise Exception(f"API error after {self.max_retries} attempts") from e

            except json.JSONDecodeError as e:
                logger.warning(
                    "ai_json_parse_error",
                    attempt=attempt,
                    max_retries=self.max_retries,
                    error=str(e),
                )
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                else:
                    raise Exception(
                        f"Failed to parse LLM response after {self.max_retries} attempts"
                    ) from e

            except Exception as e:
                logger.error(
                    "ai_extraction_unexpected_error",
                    attempt=attempt,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                else:
                    raise

        # Should never reach here due to raises above, but for type safety
        raise Exception("Extraction failed after all retries")

    def _build_extraction_prompt(
        self,
        content: str,
        schema: Dict[str, str],
        document_type: RecordType,
    ) -> str:
        """
        Build extraction prompt with clear field specifications

        Args:
            content: Document content to extract from
            schema: Field names and descriptions
            document_type: Type of document

        Returns:
            Formatted prompt string
        """
        # Build field specifications
        field_specs = []
        for field_name, description in schema.items():
            field_specs.append(f"- {field_name}: {description}")

        field_list = "\n".join(field_specs)

        # Document type specific instructions
        type_instructions = {
            RecordType.FORM: "This is an HTML contact form. Extract client contact information.",
            RecordType.EMAIL: "This is an email message. Extract relevant client or invoice information.",
            RecordType.INVOICE: "This is an HTML invoice. Extract financial data and validate calculations.",
        }

        instruction = type_instructions.get(
            document_type, "Extract structured data from this document."
        )

        prompt = f"""You are a data extraction machine. {instruction}

Extract the following fields from the document:
{field_list}

IMPORTANT INSTRUCTIONS:
1. Return ONLY valid JSON with the exact field names specified above
2. If a field is not found or cannot be determined, use null for that field
3. Include a "confidence" field (0.0-1.0) for EACH extracted value indicating your confidence
4. Use the format: {{"field_name": {{"value": "extracted_value", "confidence": 0.95}}}}
5. For missing fields, use: {{"field_name": {{"value": null, "confidence": 0.0}}}}
6. Do not include any explanatory text, only the JSON object

Document content:
{content}

JSON output:"""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """
        Call OpenAI API with the extraction prompt

        Args:
            prompt: Formatted extraction prompt

        Returns:
            Raw LLM response text

        Raises:
            APIError: On API failures
            RateLimitError: On rate limit
            APITimeoutError: On timeout
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data extraction machine. Extract structured data and return only valid JSON.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"},  # Ensure JSON response
        )

        return response.choices[0].message.content or ""

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse and validate LLM JSON response

        Args:
            response: Raw LLM response text

        Returns:
            Dictionary with extracted data and field confidences

        Raises:
            json.JSONDecodeError: If response is not valid JSON
            ValueError: If response doesn't match expected format
        """
        # Parse JSON
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(
                "json_parse_failed",
                response_preview=response[:200],
                error=str(e),
            )
            raise

        # Extract values and confidences
        extracted = {}
        field_confidences = {}

        for field_name, field_data in data.items():
            if isinstance(field_data, dict) and "value" in field_data:
                # Expected format: {"field": {"value": "x", "confidence": 0.9}}
                extracted[field_name] = field_data.get("value")
                field_confidences[field_name] = field_data.get("confidence", 0.5)
            else:
                # Fallback: treat as direct value
                extracted[field_name] = field_data
                field_confidences[field_name] = 0.5  # Default confidence

        # Add field confidences to result
        extracted["field_confidences"] = field_confidences

        return extracted

    def _calculate_confidence(
        self,
        extracted_data: Dict[str, Any],
        schema: Dict[str, str],
    ) -> float:
        """
        Calculate overall confidence score based on field confidences and completeness

        Args:
            extracted_data: Extracted data with field_confidences
            schema: Expected fields

        Returns:
            Overall confidence score (0.0-1.0)
        """
        field_confidences = extracted_data.get("field_confidences", {})

        if not field_confidences:
            # No confidence data, use field completeness
            non_null_fields = sum(
                1 for k, v in extracted_data.items() if k != "field_confidences" and v is not None
            )
            total_fields = len(schema)
            return non_null_fields / total_fields if total_fields > 0 else 0.0

        # Calculate average confidence of non-null fields
        confidences = []
        for field_name in schema.keys():
            if field_name in field_confidences:
                conf = field_confidences[field_name]
                # Only include if field has a value
                if extracted_data.get(field_name) is not None:
                    confidences.append(conf)

        if not confidences:
            return 0.0

        # Determine relevant fields for completeness calculation
        # Define optional fields that shouldn't penalize confidence if missing
        optional_fields = {"priority", "message"}
        invoice_fields = {"invoice_number", "amount", "vat", "total_amount"}

        has_invoice_data = any(extracted_data.get(field) is not None for field in invoice_fields)

        # Calculate relevant fields based on document type
        if has_invoice_data:
            # Document has invoice data - all invoice fields are required, client fields are optional
            required_fields = [
                f for f in schema.keys() if f in invoice_fields or f == "date" or f == "client_name"
            ]
        else:
            # Document is client-only - exclude invoice fields, some client fields optional
            required_fields = [
                f for f in schema.keys() if f not in invoice_fields and f not in optional_fields
            ]

        # Count how many required fields were populated
        populated_required = sum(
            1 for field in required_fields if extracted_data.get(field) is not None
        )

        # Completeness based only on required fields
        completeness = populated_required / len(required_fields) if required_fields else 1.0

        # Average confidence of populated fields (both required and optional)
        avg_confidence = sum(confidences) / len(confidences)

        # Weight confidence more heavily than completeness (70/30 split)
        # This way, high-confidence extractions aren't penalized too much for missing optional fields
        overall_confidence = (avg_confidence * 0.7) + (completeness * 0.3)

        return round(overall_confidence, 3)

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * 2^(attempt-1)
        delay = self.base_delay * (2 ** (attempt - 1))
        logger.info("retry_backoff", attempt=attempt, delay_seconds=delay)
        return delay
