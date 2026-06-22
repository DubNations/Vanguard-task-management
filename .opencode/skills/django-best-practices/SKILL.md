---
name: django-best-practices
description: Use when working with Django models, views, serializers, migrations, or any Django backend code. Covers ORM patterns, REST API design, signal usage, settings management, and common Django pitfalls.
---

# Django Best Practices

## Models
- Always define `__str__` and `Meta.ordering` on every model
- Use `UUIDField(primary_key=True)` for distributed systems
- Add `related_name` to all ForeignKey fields
- Use `choices` classes (TextChoices/IntegerChoices) for enum fields
- Never store computed values — use `@property` or annotate querysets
- Add `db_index=True` on fields frequently used in queries
- Use `on_delete` explicitly: `PROTECT` for critical data, `SET_NULL` for optional, `CASCADE` for children

## Migrations
- Run `makemigrations --check` before every commit
- Never edit generated migrations manually unless absolutely necessary
- Use `RunPython` for data migrations with reversible functions
- Name migrations descriptively: `0003_add_task_mode_participants`

## Views & API
- Use DRF ViewSets + Routers for CRUD APIs
- Use `SerializerMethodField` sparingly — prefer model properties or annotations
- Implement pagination at the viewset level, not per-view
- Use `get_queryset()` for data isolation, not filtering in `list()`
- Return 400 for validation errors, 403 for permission denied, 404 for not found

## Serializers
- Separate List and Detail serializers (List = lightweight, Detail = full)
- Use `read_only_fields` to prevent mass assignment
- Validate in `validate_<field>()` for field-level, `validate()` for cross-field
- Never expose internal IDs unless needed — use slugs or UUIDs

## Signals
- Avoid signals for business logic — use them only for cross-cutting concerns (logging, notifications)
- Prefer overriding `save()` / `create()` / `update()` for domain logic
- If using signals, always use `dispatch_uid` to prevent duplicate handlers

## Settings
- Use environment-based config (`django-environ` or `os.environ`)
- Never commit secrets to version control
- Use `DJANGO_ENV` env var to switch between dev/prod/local
- Keep `DEBUG=True` only in development

## Performance
- Use `django-debug-toolbar` in development to identify slow queries
- Add database indexes for fields used in `filter()`, `order_by()`, `group_by()`
- Use `annotate()` + `aggregate()` for server-side calculations
- Cache expensive queries with `django.cache` or `functools.lru_cache`
- Use `select_related()` for FK/OneToOne, `prefetch_related()` for M2M/reverse FK

## Common Pitfalls
- Never use `DateTimeField` without timezone awareness
- Always use `django.utils.timezone.now()` instead of `datetime.now()`
- Don't call `model.save()` with `update_fields` missing — it updates ALL fields
- Never import models at module level in signals — use string references or lazy imports
