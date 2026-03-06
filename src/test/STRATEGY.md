# Test Suite for MirrorMirrorEngine

This directory contains a comprehensive test suite for the MirrorMirrorEngine Flask application.

## Test Structure

```
src/test/
├── conftest.py              # Pytest fixtures and test configuration
├── test_models.py           # Unit tests for database models
├── test_helpers.py          # Unit tests for helper functions
├── test_chromadb_service.py # Unit tests for ChromaDB service
├── test_webex_service.py    # Unit tests for WebEx service
├── test_auth.py             # Integration tests for authentication endpoints
├── test_security.py         # Security and authorization tests
├── test_edge_cases.py       # Edge cases and boundary condition tests
└── test_utils.py            # Test utility functions
```

## Running Tests

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest src/test/
```

### Run with Coverage

```bash
pytest src/test/ --cov=src/app --cov-report=html --cov-report=term
```

Coverage report will be generated in `htmlcov/index.html`.

### Run Specific Test Categories

```bash
# Run only unit tests
pytest src/test/ -m unit

# Run only integration tests
pytest src/test/ -m integration

# Run only security tests
pytest src/test/ -m security

# Run fast tests only
pytest src/test/ -m fast
```

### Run Specific Test Files

```bash
# Run model tests
pytest src/test/test_models.py -v

# Run authentication tests
pytest src/test/test_auth.py -v

# Run security tests
pytest src/test/test_security.py -v
```

### Run with Parallel Execution

Install pytest-xdist:

```bash
pip install pytest-xdist
```

Run tests in parallel:

```bash
pytest src/test/ -n auto
```

## Test Markers

Tests are organized with the following markers:

- `@pytest.mark.unit` - Unit tests for models, helpers, services
- `@pytest.mark.integration` - Integration tests for API endpoints
- `@pytest.mark.security` - Security and authorization tests
- `@pytest.mark.fast` - Quick tests without external dependencies
- `@pytest.mark.slow` - Slower tests requiring setup

## Test Coverage Goals

- **Models**: 100% (simple unit tests)
- **Helpers**: 100% (pure functions)
- **Services**: 95% (with mocked dependencies)
- **Endpoints**: 90% (all routes, auth, error cases)
- **Overall**: >85%

## Key Test Features

### Fixtures (conftest.py)

- `app` - Flask test application with in-memory database
- `client` - Test client for API requests
- `db` - Database session with automatic rollback
- `create_account` - Factory for creating test accounts
- `create_profile` - Factory for creating test profiles
- `auth_token` - Valid JWT token for testing
- `auth_headers` - Authorization headers with JWT
- `mock_chromadb_service` - Mocked ChromaDB service
- `mock_webex_service` - Mocked WebEx service

### Test Database

Tests use an in-memory SQLite database (`sqlite:///:memory:`) for isolation and speed. Each test gets a fresh database that is automatically cleaned up.

### Mocking External Services

- **WebEx API**: All HTTP requests are mocked to avoid external dependencies
- **ChromaDB**: ChromaDB client is mocked for unit tests

## Known Test Failures (Expected)

Some tests are expected to fail initially, documenting current gaps:

### Security Issues

- ChromaDB endpoints lack authentication (tests document this gap)
- No rate limiting implemented (test is skipped)
- Password validation may be incomplete

### Missing Features

Tests that fail indicate features to implement:

- Meeting time validation (end before start)
- Password change token invalidation
- Rate limiting

## Manual Testing

See the main test plan document for manual verification procedures:

1. **WebEx OAuth Flow** - End-to-end OAuth testing
2. **ChromaDB Semantic Search** - Accuracy validation
3. **Database Cascades** - Verify cascade deletes
4. **Authentication Edge Cases** - Token expiry, concurrent logins
5. **Cross-Account Security** - Authorization checks
6. **Friend Request Logic** - Auto-accept mutual requests

## Writing New Tests

### Test Structure

```python
import pytest
import json

@pytest.mark.integration
class TestMyFeature:
    """Tests for my feature."""

    def test_success_case(self, client, auth_headers):
        """Test successful operation."""
        response = client.post('/api/endpoint',
            headers=auth_headers,
            data=json.dumps({'key': 'value'})
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'expected_field' in data

    def test_error_case(self, client):
        """Test error handling."""
        response = client.post('/api/endpoint')
        assert response.status_code == 401
```

### Using Fixtures

```python
def test_with_account(self, create_account, db):
    """Use factory fixtures."""
    account = create_account(email='test@example.com')
    assert account.email == 'test@example.com'
```

### Testing Authentication

```python
def test_protected_endpoint(self, client, create_account, create_jwt_token):
    """Test with JWT authentication."""
    account = create_account()
    token = create_jwt_token(account.id)
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    response = client.get('/api/protected', headers=headers)
    assert response.status_code == 200
```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure you're running pytest from the project root:

```bash
cd /path/to/MirrorMirrorEngine
pytest src/test/
```

### Database Errors

If tests fail with database errors, ensure:

1. No active database connections from other processes
2. In-memory database is properly configured in conftest.py

### Missing Dependencies

Install all testing dependencies:

```bash
pip install pytest pytest-flask pytest-cov pytest-mock freezegun factory-boy
```

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure tests cover success and error cases
3. Add appropriate markers (`@pytest.mark.unit`, etc.)
4. Update this README if adding new test categories
5. Maintain >85% coverage

## CI/CD Integration

To integrate with CI/CD pipelines:

```yaml
# Example for GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest src/test/ --cov=src/app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```




### NOTES

- add test for .env variables