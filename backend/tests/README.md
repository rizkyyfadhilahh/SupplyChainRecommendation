# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for the Supply Chain Recommendation System backend, ensuring code quality, reliability, and maintainability.

## Running Tests

### Run all tests
```bash
cd backend
pytest
```

### Run with coverage report
```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Run specific test file
```bash
pytest tests/test_stock_service.py
```

### Run specific test class or function
```bash
pytest tests/test_stock_service.py::TestAllocateStock::test_fully_fulfilled
```

### Run tests in parallel (faster)
```bash
pip install pytest-xdist
pytest -n auto
```

### Run with verbose output
```bash
pytest -v
```

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures (mock data, test client)
├── test_main.py                   # Basic health check tests
├── test_utils.py                  # Utility function tests
├── test_stock_service.py          # Stock allocation logic tests
├── test_api_endpoints.py          # API contract, auth, validation tests
├── test_audit_service.py          # Audit logging tests
├── test_forecast_thresholds.py    # Configurable threshold tests
└── README.md                      # This file
```

## Test Categories

### 1. **Unit Tests**
- `test_utils.py` — Pure functions (normalize, safe_mean, etc.)
- `test_stock_service.py` — Stock allocation algorithms
- `test_forecast_thresholds.py` — Config threshold accessors

### 2. **Integration Tests**
- `test_api_endpoints.py` — Full HTTP request/response cycle
- `test_audit_service.py` — Database writes + reads

### 3. **Contract Tests**
- `test_api_endpoints.py::TestInputValidation` — Pydantic schema validation
- `test_api_endpoints.py::TestAuthGuard` — API key enforcement

## Writing New Tests

### Use fixtures from conftest.py

```python
def test_my_feature(client, mock_sloc_master, mock_app_data_loaded):
    # client: authenticated TestClient
    # mock_sloc_master: sample SLOC data
    # mock_app_data_loaded: simulates data already loaded at startup
    
    response = client.get("/api/sloc-master")
    assert response.status_code == 200
```

### Mock external dependencies

```python
from unittest.mock import patch, MagicMock

def test_with_mocked_db():
    with patch("app.services.stock_service.get_cached_sloc_master") as mock_fn:
        mock_fn.return_value = (mock_df, "2024-06-15", "2024-06-15T10:00:00")
        # test code here
```

### Test CSV-only mode vs SQLite mode

```python
def test_feature_in_csv_mode():
    with patch("app.csv_only_mode.is_sqlite_enabled", return_value=False):
        # code that should work without SQLite
        pass

def test_feature_in_sqlite_mode():
    with patch("app.csv_only_mode.is_sqlite_enabled", return_value=True):
        # code that requires SQLite
        pass
```

## Coverage Goals

| Module | Target Coverage | Current |
|--------|----------------|---------|
| `app/utils.py` | >90% | ✅ |
| `app/services/stock_service.py` | >80% | ✅ |
| `app/services/audit_service.py` | >70% | ✅ |
| `app/routers/*.py` | >60% | 🔄 |
| **Overall** | >75% | 🔄 |

## CI/CD Integration

Tests run automatically on every push and pull request via GitHub Actions. See `.github/workflows/test.yml`.

### Local pre-commit hook (optional)
```bash
# .git/hooks/pre-commit
#!/bin/sh
cd backend && pytest tests/ -q || exit 1
```

## Troubleshooting

### Tests fail with "ModuleNotFoundError"
```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio
```

### Tests fail with "Database locked"
Set `USE_SQLITE=false` in environment to run in CSV-only mode:
```bash
export USE_SQLITE=false  # Linux/Mac
$env:USE_SQLITE="false"   # Windows PowerShell
pytest
```

### Tests hang or timeout
Check for infinite loops in trace logic or missing mocks for external calls.

## Best Practices

1. **Keep tests fast** — mock external I/O (database, file reads)
2. **Test one thing per test** — easier to debug when it fails
3. **Use descriptive names** — `test_allocate_stock_eudr_filter_only_picks_eudr_slocs`
4. **Don't test framework code** — focus on business logic
5. **Update tests when changing behavior** — failing tests after refactor = expected

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock guide](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
</contents>