"""
Integration tests for 'gwsa mail search' command.

Tests the email search functionality and confirms test data availability
for other test modules. Uses configuration from tests/config.yaml.
"""

import pytest
from typing import Dict, Any


@pytest.mark.integration
def test_mail_search_results_found(cli_runner, today_minus_60_days):
    """
    Search for emails matching criteria in tests/config.yaml.

    This test validates:
    1. Search query parsing and Gmail API interaction
    2. JSON response format and field presence
    3. Sufficient test data availability (configurable minimum)
    4. Test data is reasonably distributed (max per day check)

    Configuration used from tests/config.yaml:
        - search.query: Base search query
        - search.days_range: Number of days to search
        - test_data.min_results: Minimum emails expected
        - test_data.max_per_day: Maximum emails per day allowed

    Expected Results:
        - At least min_results emails returned
        - Valid JSON array response
        - Each message contains: id, subject, sender, date
        - No more than max_per_day emails per day on average
    """
    # Import config here to get fresh values
    from conftest import TEST_CONFIG

    base_query = TEST_CONFIG.get('search', {}).get('query', '')
    search_query = f'{base_query} after:{today_minus_60_days}'
    min_results = TEST_CONFIG.get('test_data', {}).get('min_results', 2)
    max_per_day = TEST_CONFIG.get('test_data', {}).get('max_per_day', 1)
    days_range = TEST_CONFIG.get('search', {}).get('days_range', 60)

    # Execute search
    result = cli_runner(["mail", "search", search_query])

    # Verify command executed successfully
    assert result["returncode"] == 0, f"Search command failed: {result['stderr']}"

    # Verify response is valid JSON
    assert result["json"] is not None, "Response is not valid JSON"

    # Verify response is a list
    assert isinstance(result["json"], list), "Expected response to be a list of messages"

    messages = result["json"]

    # Verify we have sufficient test data
    assert len(messages) >= min_results, (
        f"Expected at least {min_results} emails, found {len(messages)}. "
        f"Verify test data matches query in tests/config.yaml."
    )

    # Verify test data is reasonably distributed
    max_expected = days_range * max_per_day
    assert len(messages) <= max_expected, (
        f"Found {len(messages)} emails in {days_range} days. "
        f"Expected at most {max_expected} (max_per_day={max_per_day}). "
        f"Test data may be clustered or query may be too broad."
    )

    # Verify each message has required fields
    for idx, message in enumerate(messages):
        assert isinstance(message, dict), f"Message {idx} is not a dict: {message}"

        # Check required fields
        assert "id" in message, f"Message {idx} missing 'id' field"
        assert "subject" in message, f"Message {idx} missing 'subject' field"
        assert "sender" in message, f"Message {idx} missing 'sender' field"
        assert "date" in message, f"Message {idx} missing 'date' field"

        # Verify field types
        assert isinstance(message["id"], str), f"Message {idx}: id must be string"
        assert isinstance(message["subject"], str), f"Message {idx}: subject must be string"
        assert isinstance(message["sender"], str), f"Message {idx}: sender must be string"
        assert isinstance(message["date"], str), f"Message {idx}: date must be string"

        # Verify field values are non-empty
        assert message["id"], f"Message {idx}: id is empty"
        assert message["subject"], f"Message {idx}: subject is empty"
        assert message["sender"], f"Message {idx}: sender is empty"
        assert message["date"], f"Message {idx}: date is empty"

    # Verify no duplicate message IDs
    assert len(messages) == len(set(m["id"] for m in messages)), (
        "Duplicate message IDs in results"
    )

    # Test data available for downstream tests
    first_message_id = messages[0]["id"]
    assert first_message_id, "First message ID is empty"


@pytest.mark.integration
def test_mail_search_empty_results(cli_runner):
    """
    Verify search handles empty results gracefully.

    This test confirms that when a search returns no results,
    the response is valid JSON (empty list) rather than an error.
    """
    # Use a query unlikely to match anything
    search_query = 'from:"nonexistent-email-address-xyz-12345@example.com"'

    result = cli_runner(["mail", "search", search_query])

    # Command should succeed
    assert result["returncode"] == 0, f"Search command failed: {result['stderr']}"

    # Response should be valid JSON
    assert result["json"] is not None, "Response is not valid JSON"

    # Should be empty list
    assert isinstance(result["json"], list), "Expected response to be a list"
    assert len(result["json"]) == 0, f"Expected empty results, got {len(result['json'])} messages"
