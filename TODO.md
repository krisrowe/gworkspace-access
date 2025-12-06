# TODO

## Future Enhancement: Application Default Credentials (ADC) Support

Consider adding ADC as an alternative to the current OAuth token flow. See [AUTHENTICATION.md](AUTHENTICATION.md) for detailed compatibility testing results.

### Implementation Plan

Support both paths - ADC with fallback to token file:

```python
def load_credentials(token_path=None):
    # Try explicit token file first
    if token_path and os.path.exists(token_path):
        return Credentials.from_authorized_user_file(token_path, SCOPES)

    # Fall back to ADC
    credentials, _ = google.auth.default(scopes=SCOPES)
    return credentials
```

### When to Implement

- When simplifying onboarding for new users
- When majority of users are on Workspace or regular Gmail (not APP)
- Keep `create-token` as fallback for APP users and Gmail with security keys

---

## Testing

Add unit tests to cover the following scenarios:

### Scope Validation (`@require_scopes` decorator)

-   **Positive Case:** A test that calls a decorated function when the `config.yaml` contains the required scopes, and asserts that the function executes.
-   **Negative Case:** A test that calls a decorated function when the `config.yaml` is missing the required scopes. It should assert that `SystemExit` is called and that the error message contains the expected "Required: ..." and "Found: ..." strings.
-   **Implicit Grant Case:** A test that calls a function decorated with `@require_scopes('mail-read')` when the config only contains the `mail-modify` scope, and asserts that the function executes successfully.

### Atomic Setup (`_atomic_client_creds_setup`)

-   **Success Case:** A test that mocks a successful browser login (`flow.run_local_server`) and asserts that the temporary files are correctly renamed to `client_secrets.json` and `user_token.json`.
-   **Failure Case (Rollback):** A test that mocks a failed browser login (e.g., by raising an exception) and asserts that any pre-existing `client_secrets.json` and `user_token.json` are not modified, and that the temporary directory is removed.
