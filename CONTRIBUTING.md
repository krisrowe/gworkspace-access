## Project Structure

```
/gworkspace-access/
├── .env                          # Project configuration (git-ignored)
├── .gitignore                    # Specifies ignored files like .env, credentials.json, user_token.json, *.log
├── credentials.json              # Client credentials (git-ignored), managed by `gwsa setup` from Secret Manager
├── README.md                     # Main project documentation
├── CONTRIBUTING.md               # This file - contribution guidelines and project structure
├── pyproject.toml                # Project metadata and build configuration for packaging
├── gwsa_cli/                     # Main CLI package
│   ├── __main__.py               # Main CLI entry point and command dispatcher
│   ├── setup_local.py            # Core setup logic for authentication and credential management
│   └── mail/                     # Python package for Gmail operations
│       ├── __init__.py           # Initializes the mail package, contains shared authentication logic
│       ├── search.py             # Implements the 'mail search' command logic
│       ├── read.py               # Implements the 'mail read' command logic (returns {id, subject, sender, date, snippet, body: {text, html}, labelIds, raw})
│       └── label.py              # Implements the 'mail label' command logic
├── tests/                        # Integration test suite
│   ├── config.yaml               # Centralized test configuration (search query, days_range, label name, test data expectations)
│   ├── conftest.py               # pytest configuration and shared fixtures
│   └── integration/              # Integration tests for CLI commands
│       ├── test_mail_search.py    # Tests for 'gwsa mail search' command
│       ├── test_mail_read.py      # Tests for 'gwsa mail read' command
│       └── test_mail_modify.py    # Tests for 'gwsa mail label' command (apply and remove)
├── user_token.json               # User credentials (git-ignored), managed by `gwsa setup` during OAuth flow
└── test_results.log              # Test output log (git-ignored)
```

## Development Setup

Install the project in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

## Running Tests

The integration test suite requires a configured environment (`gwsa setup` must have been run).

Run all tests:
```bash
python -m pytest tests/integration/ -v
```

Tests use configuration from `tests/config.yaml` to be generic and reusable for different email sources. Adjust the search query, label name, and test data expectations in that file.

## Contributing Guidelines

_Further contributing guidelines can be added here._
