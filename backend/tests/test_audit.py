"""审计日志测试 — AuditLogMiddleware。"""
import logging
import pytest


def _capture_audit_logs(caplog):
    """上下文管理器：临时让 audit logger propagate 到 root，以便 caplog 捕获。"""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        audit_logger = logging.getLogger('audit')
        old_propagate = audit_logger.propagate
        audit_logger.propagate = True
        try:
            with caplog.at_level(logging.INFO, logger='audit'):
                yield
        finally:
            audit_logger.propagate = old_propagate

    return _ctx()


# ---------------------------------------------------------------------------
# AuditLogMiddleware 审计日志测试
# ---------------------------------------------------------------------------
class TestAuditLogMiddleware:
    """验证 AuditLogMiddleware 记录 API 请求到 audit logger。"""

    def test_api_request_produces_audit_log(self, auth_client, caplog):
        """API 请求产生审计日志条目。"""
        with _capture_audit_logs(caplog):
            auth_client.get('/api/v1/auth/me/')
        audit_records = [r for r in caplog.records if r.name == 'audit']
        assert any(
            'API GET' in r.message and '/api/v1/auth/me/' in r.message
            for r in audit_records
        )

    def test_health_check_excluded(self, api_client, caplog, db):
        """健康检查路径不记录审计日志。"""
        with _capture_audit_logs(caplog):
            api_client.get('/api/v1/health')
        audit_records = [r for r in caplog.records if r.name == 'audit']
        assert not any('/api/v1/health' in r.message for r in audit_records)

    def test_anonymous_user_logged_as_anonymous(self, api_client, caplog, db):
        """匿名用户 → username 为空或 anonymous。"""
        with _capture_audit_logs(caplog):
            # 访问受保护端点会返回 401，但仍会记录审计日志
            api_client.get('/api/v1/tasks/')
        audit_records = [r for r in caplog.records if r.name == 'audit']
        # Django AnonymousUser.username 返回空字符串，
        # middleware 使用 getattr(user, 'username', 'anonymous')，
        # 所以日志可能是 'user=' (空) 或 'user=anonymous'
        assert any(
            ('user= ' in r.message or 'user=anonymous' in r.message)
            and 'id=None' in r.message
            for r in audit_records
        )

    def test_authenticated_user_includes_user_info(self, auth_client, admin_user, caplog):
        """已认证用户 → 日志包含 user_id 和 username。"""
        with _capture_audit_logs(caplog):
            auth_client.get('/api/v1/auth/me/')
        audit_records = [r for r in caplog.records if r.name == 'audit']
        # 日志格式: user=<username> (id=<uuid>)
        assert any(
            admin_user.username in r.message and str(admin_user.id) in r.message
            for r in audit_records
        )

    def test_ip_from_x_forwarded_for(self, auth_client, caplog):
        """X-Forwarded-For → 取第一个 IP。"""
        with _capture_audit_logs(caplog):
            auth_client.get(
                '/api/v1/auth/me/',
                HTTP_X_FORWARDED_FOR='203.0.113.50, 70.41.3.18, 150.172.238.178',
            )
        audit_records = [r for r in caplog.records if r.name == 'audit']
        assert any('203.0.113.50' in r.message for r in audit_records)

    def test_ip_from_remote_addr_without_proxy(self, auth_client, caplog):
        """无代理时 → 使用 REMOTE_ADDR。"""
        with _capture_audit_logs(caplog):
            auth_client.get('/api/v1/auth/me/', REMOTE_ADDR='192.168.1.100')
        audit_records = [r for r in caplog.records if r.name == 'audit']
        assert any('192.168.1.100' in r.message for r in audit_records)

    def test_response_time_recorded(self, auth_client, caplog):
        """响应时间 → duration_ms ≥ 0，日志含数字+ms 模式。"""
        with _capture_audit_logs(caplog):
            auth_client.get('/api/v1/auth/me/')
        audit_records = [r for r in caplog.records if r.name == 'audit']
        assert len(audit_records) > 0
        # 日志格式含 'Xms'，验证存在数字+ms 模式
        import re
        assert any(
            re.search(r'\d+ms', r.message) for r in audit_records
        )
