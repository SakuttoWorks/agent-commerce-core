import json
from unittest.mock import AsyncMock, patch

from app.utils.guardian import verify_gateway
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# 1. Override the Zero-Trust Gateway dependency for local testing
def override_verify_gateway():
    return "test-tenant-123"


app.dependency_overrides[verify_gateway] = override_verify_gateway


@patch("main.verify_url_is_live", new_callable=AsyncMock)
@patch("main.data_guardian.enforce_compliance")
@patch("main.extract_via_jina")
@patch("main.normalizer.normalize")
def test_field_filtering_success(
    mock_normalize, mock_extract, mock_compliance, mock_verify
):
    """
    Test if the 'fields' query parameter successfully filters out unrequested keys
    from the JSON response returned by the Gemini normalizer.
    """
    # Mock external calls to isolate the core logic
    mock_verify.return_value = None
    mock_compliance.return_value = None
    mock_extract.return_value = "Mocked website content from Jina"

    # Mock the Gemini normalizer output (It returns a JSON string in production)
    mock_gemini_json_string = json.dumps(
        {
            "title": "Sakutto Works Documentation",
            "core_summary": "This is a detailed summary of the architecture.",
            "structured_data": [{"key": "version", "value": "3.0.0"}],
        }
    )

    # normalizer.normalize returns: success(bool), data(str), metadata(dict)
    mock_normalize.return_value = (True, mock_gemini_json_string, {"engine": "test"})

    # Execute the request asking ONLY for the 'title' field
    response = client.post(
        "/v1/normalize_web_data?fields=title",
        json={"url": "https://sakutto.works", "format_type": "json"},
    )

    # Assertions
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["success"] is True

    # The 'data' payload should be a dictionary containing ONLY the 'title' key
    extracted_payload = response_data["data"]
    assert "title" in extracted_payload
    assert extracted_payload["title"] == "Sakutto Works Documentation"

    # These keys should have been filtered out
    assert "core_summary" not in extracted_payload
    assert "structured_data" not in extracted_payload


@patch("main.verify_url_is_live", new_callable=AsyncMock)
@patch("main.data_guardian.enforce_compliance")
@patch("main.extract_via_jina")
@patch("main.normalizer.normalize")
def test_field_filtering_fallback(
    mock_normalize, mock_extract, mock_compliance, mock_verify
):
    """
    Test the fallback behavior: If the requested fields are not present in the
    extracted JSON, it should safely return the complete payload instead of an empty dict.
    """
    mock_verify.return_value = None
    mock_compliance.return_value = None
    mock_extract.return_value = "Mocked website content from Jina"

    mock_gemini_json_string = json.dumps(
        {"title": "Sakutto Works Documentation", "core_summary": "Summary text here."}
    )
    mock_normalize.return_value = (True, mock_gemini_json_string, {"engine": "test"})

    # Request a key that does not exist ('non_existent_key')
    response = client.post(
        "/v1/normalize_web_data?fields=non_existent_key",
        json={"url": "https://sakutto.works", "format_type": "json"},
    )

    assert response.status_code == 200
    response_data = response.json()

    # The fallback should trigger and return all original keys
    extracted_payload = response_data["data"]
    assert "title" in extracted_payload
    assert "core_summary" in extracted_payload


@patch("main.verify_url_is_live", new_callable=AsyncMock)
@patch("main.data_guardian.enforce_compliance")
@patch("main.extract_via_jina")
@patch("main.normalizer.normalize")
def test_field_filtering_multiple_fields(
    mock_normalize, mock_extract, mock_compliance, mock_verify
):
    """
    Test filtering with multiple comma-separated fields.
    """
    mock_verify.return_value = None
    mock_compliance.return_value = None
    mock_extract.return_value = "Mocked content"
    mock_gemini_json_string = json.dumps(
        {
            "title": "Sakutto Works",
            "core_summary": "Summary text",
            "structured_data": [{"key": "v", "value": "1"}],
        }
    )
    mock_normalize.return_value = (True, mock_gemini_json_string, {"engine": "test"})

    # Request multiple fields
    response = client.post(
        "/v1/normalize_web_data?fields=title,core_summary",
        json={"url": "https://sakutto.works", "format_type": "json"},
    )

    assert response.status_code == 200
    extracted_payload = response.json()["data"]

    assert "title" in extracted_payload
    assert "core_summary" in extracted_payload
    assert "structured_data" not in extracted_payload


@patch("main.verify_url_is_live", new_callable=AsyncMock)
@patch("main.data_guardian.enforce_compliance")
@patch("main.extract_via_jina")
@patch("main.normalizer.normalize")
def test_field_filtering_markdown_fallback(
    mock_normalize, mock_extract, mock_compliance, mock_verify
):
    """
    Test that filtering gracefully skips and returns the raw string
    if the extracted data is Markdown (not JSON).
    """
    mock_verify.return_value = None
    mock_compliance.return_value = None
    mock_extract.return_value = "Mocked content"

    # Simulate Gemini returning plain Markdown text
    mock_markdown_string = "# Sakutto Works\nThis is a markdown summary."
    mock_normalize.return_value = (True, mock_markdown_string, {"engine": "test"})

    response = client.post(
        "/v1/normalize_web_data?fields=title",
        json={"url": "https://sakutto.works", "format_type": "markdown"},
    )

    assert response.status_code == 200
    response_data = response.json()

    # Should return the raw markdown string without crashing
    assert response_data["data"] == mock_markdown_string


@patch("main.verify_url_is_live", new_callable=AsyncMock)
@patch("main.data_guardian.enforce_compliance")
@patch("main.extract_via_jina")
@patch("main.normalizer.normalize")
def test_url_whitespace_stripping(
    mock_normalize, mock_extract, mock_compliance, mock_verify
):
    """
    Test that a URL with leading or trailing whitespace is successfully stripped
    and processed as a normalized URL without causing validation errors.
    """
    mock_verify.return_value = None
    mock_compliance.return_value = None
    mock_extract.return_value = "Mocked website content from Jina"

    mock_markdown_string = "# Sakutto Works\nWhitespace test normalized content."
    mock_normalize.return_value = (True, mock_markdown_string, {"engine": "test"})

    # Execute the request with spaces around the URL
    response = client.post(
        "/v1/normalize_web_data",
        json={"url": "  https://sakutto.works  ", "format_type": "markdown"},
    )

    # Assertions
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["success"] is True
    assert response_data["data"] == mock_markdown_string


@patch("main.verify_url_is_live", new_callable=AsyncMock)
@patch("main.data_guardian.enforce_compliance")
@patch("main.extract_via_jina")
@patch("main.normalizer.normalize")
def test_format_type_normalization(
    mock_normalize, mock_extract, mock_compliance, mock_verify
):
    """
    Test that format_type is automatically stripped of whitespace and converted to lowercase.
    """
    mock_verify.return_value = None
    mock_compliance.return_value = None
    mock_extract.return_value = "Mocked website content from Jina"

    mock_markdown_string = "# Sakutto Works"
    mock_normalize.return_value = (True, mock_markdown_string, {"engine": "test"})

    # Send 'format_type' with uppercase letters and surrounding spaces
    response = client.post(
        "/v1/normalize_web_data",
        json={"url": "https://sakutto.works", "format_type": " Markdown "},
    )

    assert response.status_code == 200
    assert response.json()["data"] == mock_markdown_string
