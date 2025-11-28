"""
Integration tests for 'gwsa mail read' command.

Tests the message reading functionality and validates all expected
fields are present in the JSON response.
"""

import pytest
import re


@pytest.mark.integration
def test_mail_read_full_details(cli_runner, test_email_id):
    """
    Test reading a complete email message with all fields.

    This test validates:
    1. Message can be read successfully
    2. Response is valid JSON
    3. All expected fields are present
    4. Field types are correct
    5. Field values are non-empty where expected
    6. Content matches expectations

    Expected JSON Structure:
        {
            "id": string,
            "subject": string,
            "sender": string,
            "date": string (RFC 2822),
            "snippet": string (may be empty),
            "body": {
                "text": string or None,
                "html": string or None
            },
            "labelIds": array of strings,
            "raw": string (full JSON representation)
        }
    """
    message_id = test_email_id

    # Execute read command
    result = cli_runner(["mail", "read", message_id])

    # Verify command succeeded
    assert result["returncode"] == 0, f"Read command failed: {result['stderr']}"

    # Verify response is valid JSON
    assert result["json"] is not None, "Response is not valid JSON"

    # Verify response is a dict
    assert isinstance(result["json"], dict), "Expected response to be a dict"

    message = result["json"]

    # ===== REQUIRED FIELD: id =====
    assert "id" in message, "Missing required field: 'id'"
    assert isinstance(message["id"], str), "Field 'id' must be a string"
    assert message["id"], "Field 'id' is empty"
    assert len(message["id"]) > 0, "Field 'id' has zero length"

    # ===== REQUIRED FIELD: subject =====
    assert "subject" in message, "Missing required field: 'subject'"
    assert isinstance(message["subject"], str), "Field 'subject' must be a string"
    assert message["subject"], "Field 'subject' is empty"
    assert "Your Daily Digest" in message["subject"], (
        f"Subject doesn't contain expected text: {message['subject']}"
    )

    # ===== REQUIRED FIELD: sender =====
    assert "sender" in message, "Missing required field: 'sender'"
    assert isinstance(message["sender"], str), "Field 'sender' must be a string"
    assert message["sender"], "Field 'sender' is empty"
    assert "USPS" in message["sender"], (
        f"Sender doesn't contain 'USPS': {message['sender']}"
    )

    # ===== REQUIRED FIELD: date =====
    assert "date" in message, "Missing required field: 'date'"
    assert isinstance(message["date"], str), "Field 'date' must be a string"
    assert message["date"], "Field 'date' is empty"

    # Validate date format (RFC 2822 or similar)
    # Example: "Fri, 28 Nov 2025 13:29:02 +0000"
    assert re.match(r'\w+,\s+\d+\s+\w+\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+[+-]\d{4}', message["date"]), (
        f"Date doesn't match expected format (RFC 2822): {message['date']}"
    )

    # ===== OPTIONAL FIELD: snippet =====
    assert "snippet" in message, "Missing field: 'snippet'"
    assert isinstance(message["snippet"], str), "Field 'snippet' must be a string"
    # snippet can be empty, but for USPS emails it should have content
    # We allow empty for robustness

    # ===== REQUIRED FIELD: body =====
    assert "body" in message, "Missing required field: 'body'"
    assert isinstance(message["body"], dict), "Field 'body' must be a dict with 'text' and 'html' keys"

    # Body should have text and html fields
    assert "text" in message["body"], "Body missing 'text' field"
    assert "html" in message["body"], "Body missing 'html' field"

    # Both fields should be strings or None
    assert message["body"]["text"] is None or isinstance(message["body"]["text"], str), \
        "body.text must be string or None"
    assert message["body"]["html"] is None or isinstance(message["body"]["html"], str), \
        "body.html must be string or None"

    # At least one should have content (text preferred, html fallback)
    has_text = message["body"]["text"] and len(message["body"]["text"]) > 0
    has_html = message["body"]["html"] and len(message["body"]["html"]) > 0

    assert has_text or has_html, (
        "Body has neither text nor html content. "
        "Snippet field provides fallback: " + message["snippet"]
    )

    # ===== REQUIRED FIELD: labelIds =====
    assert "labelIds" in message, "Missing required field: 'labelIds'"
    assert isinstance(message["labelIds"], list), "Field 'labelIds' must be a list"
    # labelIds can be empty, but USPS emails typically have labels (INBOX, CATEGORY_UPDATES, etc.)

    # Verify labelIds contains strings
    for idx, label_id in enumerate(message["labelIds"]):
        assert isinstance(label_id, str), (
            f"labelIds[{idx}] is not a string: {label_id}"
        )
        assert label_id, f"labelIds[{idx}] is empty"

    # ===== REQUIRED FIELD: raw =====
    assert "raw" in message, "Missing required field: 'raw'"
    assert isinstance(message["raw"], str), "Field 'raw' must be a string"
    assert message["raw"], "Field 'raw' is empty"

    # Verify raw can be parsed as JSON
    import json
    try:
        raw_json = json.loads(message["raw"])
        assert isinstance(raw_json, dict), "Raw field should contain JSON object"
    except json.JSONDecodeError as e:
        pytest.fail(f"Raw field is not valid JSON: {e}")

    # ===== VERIFY NO EXTRA UNEXPECTED FIELDS =====
    expected_fields = {"id", "subject", "sender", "date", "snippet", "body", "labelIds", "raw"}
    actual_fields = set(message.keys())

    extra_fields = actual_fields - expected_fields
    if extra_fields:
        # Extra fields are OK (for future extensibility), just note them
        print(f"Note: Extra fields in response: {extra_fields}")

    missing_fields = expected_fields - actual_fields
    assert not missing_fields, f"Missing expected fields: {missing_fields}"


@pytest.mark.integration
def test_mail_read_email_not_found(cli_runner):
    """
    Test reading a non-existent message ID.

    Validates that the CLI returns appropriate error when message doesn't exist.
    """
    # Use a fake message ID
    fake_id = "0000000000000000"

    result = cli_runner(["mail", "read", fake_id])

    # Should fail with non-zero exit code
    assert result["returncode"] != 0, (
        "Expected command to fail for non-existent message"
    )

    # Error message should be in stderr
    assert result["stderr"], "Expected error message in stderr"
