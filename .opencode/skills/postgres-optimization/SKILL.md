---
name: postgres-optimization
description: Use when writing database queries, designing schemas, or optimizing PostgreSQL performance in a Django project. Covers indexing strategies, query optimization, connection pooling, and migration safety.
---

# PostgreSQL Optimization for Django

## Indexing Strategy
- Add btree index on foreign keys (Django doesn't do this automatically)
- Use composite indexes for multi-column `WHERE` clauses: `Index(fields=['status', 'priority'])`
- Use `db_index=True` on fields with high cardinality used in `filter()`/`order_by()`
- Consider partial indexes for filtered queries: `indexes = [models.Index(fields=['status'], condition=Q(status='PENDING'))]`
- Use GIN/GiST indexes for JSONField queries

## Query Optimization
- Always use `select_related()` for ForeignKey and OneToOneField lookups
- Use `prefetch_related()` for ManyToManyField and reverse ForeignKey
- Use `only()` / `defer()` to limit columns fetched
- Use `values()` / `values_list()` when you don't need full model instances
- Avoid `count()` on large tables — use `exists()` for existence checks
- Use `F()` expressions for atomic updates instead of read-modify-write
- Use `Subquery` and `OuterRef` for correlated subqueries instead of Python loops

## Connection Pooling
- Use `django-db-connection-pool` or `pgbouncer` in production
- Set `CONN_MAX_AGE` in DATABASE settings for persistent connections
- Monitor connection count: `SELECT count(*) FROM pg_stat_activity;`

## N+1 Query Prevention
- Profile with `django-debug-toolbar` or `django.db.connection.queries`
- Use `prefetch_related_objects()` for dynamic prefetching
- Use `django-extensions` shell_plus with `--print-sql` to see generated queries

## Migration Safety
- Add indexes CONCURRENTLY in production: use `AddIndexConcurrently` with `atomic=False`
- Never drop columns without first deploying code that stops using them
- Use `AlterField` instead of `RenameField` to avoid data loss
- Test migrations with `python manage.py migrate --plan` before applying

## Monitoring
- Enable `log_queries` in development, use `pg_stat_statements` in production
- Run `EXPLAIN ANALYZE` on slow queries to check execution plans
- Watch for sequential scans on large tables: `SELECT relname, seq_scan FROM pg_stat_user_tables WHERE seq_scan > 0;`
