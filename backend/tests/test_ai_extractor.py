import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.models.extraction import RecordType
from app.parsers.llm_based.extractor import AIExtractor


@pytest.fixture
def ai_extractor():
    """Create AIExtractor instance with mocked settings"""
    with patch("app.parsers.llm_based.extractor.get_settings") as mock_settings:
        settings = Mock()
        settings.openai_api_key = "sk-test-key"
        settings.openai_model = "gpt-4o-mini"
        settings.openai_temperature = 0.1
        settings.openai_timeout = 30
        mock_settings.return_value = settings

        with patch("app.parsers.llm_based.extractor.OpenAI"):
            extractor = AIExtractor()
            yield extractor


def test_build_extraction_prompt_form(ai_extractor):
    """Test prompt building for form extraction"""
    schema = {
        "client_name": "Full name of the client",
        "email": "Email address",
        "phone": "Phone number",
    }
    content = "<html><body>Test form</body></html>"

    prompt = ai_extractor._build_extraction_prompt(
        content, schema, RecordType.FORM
    )

    assert "client_name" in prompt
    assert "email" in prompt
    assert "phone" in prompt
    assert "HTML contact form" in prompt
    assert content in prompt
    assert "JSON" in prompt


def test_build_extraction_prompt_invoice(ai_extractor):
    """Test prompt building for invoice extraction"""
    schema = {
        "invoice_number": "Invoice number",
        "amount": "Base amount",
        "total_amount": "Total amount",
    }
    content = "<html><body>Invoice content</body></html>"

    prompt = ai_extractor._build_extraction_prompt(
        content, schema, RecordType.INVOICE
    )

    assert "invoice_number" in prompt
    assert "amount" in prompt
    assert "HTML invoice" in prompt
    assert content in prompt


def test_parse_llm_response_with_confidence(ai_extractor):
    """Test parsing LLM response with confidence scores"""
    response = json.dumps({
        "client_name": {"value": "John Doe", "confidence": 0.95},
        "email": {"value": "john@example.com", "confidence": 0.9},
        "phone": {"value": "+30 123456789", "confidence": 0.85},
    })

    result = ai_extractor._parse_llm_response(response)

    assert result["client_name"] == "John Doe"
    assert result["email"] == "john@example.com"
    assert result["phone"] == "+30 123456789"
    assert result["field_confidences"]["client_name"] == 0.95
    assert result["field_confidences"]["email"] == 0.9
    assert result["field_confidences"]["phone"] == 0.85


def test_parse_llm_response_with_null_values(ai_extractor):
    """Test parsing LLM response with null values"""
    response = json.dumps({
        "client_name": {"value": "John Doe", "confidence": 0.95},
        "email": {"value": None, "confidence": 0.0},
        "phone": {"value": None, "confidence": 0.0},
    })

    result = ai_extractor._parse_llm_response(response)

    assert result["client_name"] == "John Doe"
    assert result["email"] is None
    assert result["phone"] is None
    assert result["field_confidences"]["client_name"] == 0.95


def test_parse_llm_response_fallback_format(ai_extractor):
    """Test parsing LLM response with fallback format (direct values)"""
    response = json.dumps({
        "client_name": "John Doe",
        "email": "john@example.com",
    })

    result = ai_extractor._parse_llm_response(response)

    assert result["client_name"] == "John Doe"
    assert result["email"] == "john@example.com"
    # Should have default confidence
    assert result["field_confidences"]["client_name"] == 0.5
    assert result["field_confidences"]["email"] == 0.5


def test_parse_llm_response_invalid_json(ai_extractor):
    """Test parsing invalid JSON raises error"""
    response = "This is not valid JSON"

    with pytest.raises(json.JSONDecodeError):
        ai_extractor._parse_llm_response(response)


def test_calculate_confidence_with_field_confidences(ai_extractor):
    """Test confidence calculation with field confidence scores"""
    extracted_data = {
        "client_name": "John Doe",
        "email": "john@example.com",
        "phone": "+30 123456789",
        "field_confidences": {
            "client_name": 0.95,
            "email": 0.9,
            "phone": 0.85,
        },
    }
    schema = {
        "client_name": "Name",
        "email": "Email",
        "phone": "Phone",
    }

    confidence = ai_extractor._calculate_confidence(extracted_data, schema)

    # Average confidence: (0.95 + 0.9 + 0.85) / 3 = 0.9
    # Completeness: 3/3 = 1.0
    # Overall: (0.9 + 1.0) / 2 = 0.95
    assert confidence == 0.95


def test_calculate_confidence_with_missing_fields(ai_extractor):
    """Test confidence calculation with missing fields"""
    extracted_data = {
        "client_name": "John Doe",
        "email": None,
        "phone": "+30 123456789",
        "field_confidences": {
            "client_name": 0.95,
            "email": 0.0,
            "phone": 0.85,
        },
    }
    schema = {
        "client_name": "Name",
        "email": "Email",
        "phone": "Phone",
    }

    confidence = ai_extractor._calculate_confidence(extracted_data, schema)

    # Only non-null fields: client_name (0.95), phone (0.85)
    # Average confidence: (0.95 + 0.85) / 2 = 0.9
    # Completeness: 2/3 = 0.667
    # Overall: (0.9 + 0.667) / 2 = 0.783
    assert 0.78 <= confidence <= 0.79


def test_calculate_confidence_without_field_confidences(ai_extractor):
    """Test confidence calculation without field confidence data"""
    extracted_data = {
        "client_name": "Giannis Mixalis",
        "email": "giannis@example.com",
        "phone": None,
    }
    schema = {
        "client_name": "Name",
        "email": "Email",
        "phone": "Phone",
    }

    confidence = ai_extractor._calculate_confidence(extracted_data, schema)

    # Completeness only: 2/3 = 0.667
    assert 0.66 <= confidence <= 0.67


def test_calculate_backoff_delay(ai_extractor):
    """Test exponential backoff delay calculation"""
    # Attempt 1: 1 * 2^0 = 1 second
    assert ai_extractor._calculate_backoff_delay(1) == 1.0

    # Attempt 2: 1 * 2^1 = 2 seconds
    assert ai_extractor._calculate_backoff_delay(2) == 2.0

    # Attempt 3: 1 * 2^2 = 4 seconds
    assert ai_extractor._calculate_backoff_delay(3) == 4.0


@patch("app.parsers.llm_based.extractor.OpenAI")
@patch("app.parsers.llm_based.extractor.get_settings")
def test_extract_structured_data_success(mock_settings, mock_openai_class):
    """Test successful extraction with retry logic"""
    # Setup mocks
    settings = Mock()
    settings.openai_api_key = "sk-test-key"
    settings.openai_model = "gpt-4o-mini"
    settings.openai_temperature = 0.1
    settings.openai_timeout = 30
    mock_settings.return_value = settings

    # Mock OpenAI response
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "client_name": {"value": "John Doe", "confidence": 0.95},
        "email": {"value": "john@example.com", "confidence": 0.9},
    })
    mock_client.chat.completions.create.return_value = mock_response

    # Create extractor and test
    extractor = AIExtractor()
    schema = {
        "client_name": "Full name",
        "email": "Email address",
    }
    content = "<html>Test content</html>"

    result, confidence = extractor.extract_structured_data(
        content, schema, RecordType.FORM
    )

    assert result["client_name"] == "John Doe"
    assert result["email"] == "john@example.com"
    assert confidence > 0.8
    assert mock_client.chat.completions.create.called


@patch("app.parsers.llm_based.extractor.time.sleep")
@patch("app.parsers.llm_based.extractor.OpenAI")
@patch("app.parsers.llm_based.extractor.get_settings")
def test_extract_structured_data_retry_on_rate_limit(
    mock_settings, mock_openai_class, mock_sleep
):
    """Test retry logic on rate limit error"""
    # Setup mocks
    settings = Mock()
    settings.openai_api_key = "sk-test-key"
    settings.openai_model = "gpt-4o-mini"
    settings.openai_temperature = 0.1
    settings.openai_timeout = 30
    mock_settings.return_value = settings

    # Mock OpenAI to fail twice then succeed
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    from openai import RateLimitError

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "client_name": {"value": "John Doe", "confidence": 0.95},
    })

    mock_client.chat.completions.create.side_effect = [
        RateLimitError("Rate limit", response=Mock(), body=None),
        RateLimitError("Rate limit", response=Mock(), body=None),
        mock_response,
    ]

    # Create extractor and test
    extractor = AIExtractor()
    schema = {"client_name": "Full name"}
    content = "<html>Test content</html>"

    result, confidence = extractor.extract_structured_data(
        content, schema, RecordType.FORM
    )

    assert result["client_name"] == "John Doe"
    assert mock_client.chat.completions.create.call_count == 3
    assert mock_sleep.call_count == 2  # Two retries


@patch("app.parsers.llm_based.extractor.time.sleep")
@patch("app.parsers.llm_based.extractor.OpenAI")
@patch("app.parsers.llm_based.extractor.get_settings")
def test_extract_structured_data_max_retries_exceeded(
    mock_settings, mock_openai_class, mock_sleep
):
    """Test that extraction fails after max retries"""
    # Setup mocks
    settings = Mock()
    settings.openai_api_key = "sk-test-key"
    settings.openai_model = "gpt-4o-mini"
    settings.openai_temperature = 0.1
    settings.openai_timeout = 30
    mock_settings.return_value = settings

    # Mock OpenAI to always fail
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    from openai import RateLimitError

    mock_client.chat.completions.create.side_effect = RateLimitError(
        "Rate limit", response=Mock(), body=None
    )

    # Create extractor and test
    extractor = AIExtractor()
    schema = {"client_name": "Full name"}
    content = "<html>Test content</html>"

    with pytest.raises(Exception) as exc_info:
        extractor.extract_structured_data(content, schema, RecordType.FORM)

    assert "Rate limit exceeded" in str(exc_info.value)
    assert mock_client.chat.completions.create.call_count == 3
    assert mock_sleep.call_count == 2
