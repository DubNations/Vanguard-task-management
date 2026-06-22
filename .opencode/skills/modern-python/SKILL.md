---
name: modern-python
description: Use when writing, reviewing, or refactoring Python code. Enforces modern Python practices (3.10+), type hints, dataclasses, async patterns, ruff linting, and pytest testing. Covers Django ORM optimization, queryset efficiency, and N+1 query prevention.
---

# Modern Python Best Practices

## Type Annotations
- Use `str | None` instead of `Optional[str]` (Python 3.10+)
- Use `list[str]` instead of `List[str]` for built-in generics
- Use `@dataclass` or `NamedTuple` for structured data
- Always annotate function signatures; skip variable annotations when obvious

## Code Style
- Prefer `pathlib.Path` over `os.path`
- Use `functools.cache` / `lru_cache` for pure function memoization
- Use `enum.Enum` / `StrEnum` for string constants instead of bare strings
- Prefer f-strings over `.format()` or `%` formatting
- Use context managers (`with`) for resource cleanup

## Django-Specific
- Always use `select_related()` / `prefetch_related()` to avoid N+1 queries
- Use `bulk_create()` / `bulk_update()` for batch operations
- Prefer `get_or_create()` / `update_or_create()` over manual check-then-create
- Use `QuerySet.iterator()` for large datasets to avoid memory exhaustion
- Add `db_index=True` on fields used in `filter()`, `order_by()`, `exclude()`
- Use `@transaction.atomic()` for multi-step writes
- Never call `.save()` in a loop — use `bulk_update()`

## Error Handling
- Catch specific exceptions, never bare `except:`
- Use custom exception classes for business logic errors
- Log exceptions with `logger.exception()` which includes traceback
- Implement graceful degradation, not silent failure

## Testing
- Use `pytest` + `pytest-django` over unittest
- Use `@pytest.fixture` for test setup, factories for complex data
- Use `pytest.mark.parametrize` for data-driven tests
- Test edge cases: empty inputs, None values, boundary conditions
- Use `pytest-cov` for coverage reporting

## Security
- Never hardcode secrets; use environment variables
- Use `secrets.token_urlsafe()` for token generation, not `random`
- Validate and sanitize all user inputs at API boundaries
- Use Django's built-in protections (CSRF, XSS, SQL injection prevention)
- Never log sensitive data (passwords, tokens, PII)
