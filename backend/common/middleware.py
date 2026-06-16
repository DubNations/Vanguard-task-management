import logging
import time
import threading

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('audit')

_thread_local = threading.local()


def get_current_user():
    return getattr(_thread_local, 'user', None)


def get_current_request():
    return getattr(_thread_local, 'request', None)


class AuditLogMiddleware(MiddlewareMixin):
    """记录每个 API 请求到审计日志。"""

    EXCLUDE_PATHS = ['/api/v1/health', '/static/', '/__debug__/', '/nginx-health']

    def process_request(self, request):
        _thread_local.request = request
        _thread_local.user = getattr(request, 'user', None)
        request._audit_start_time = time.time()

    def process_response(self, request, response):
        path = request.path
        if any(path.startswith(p) for p in self.EXCLUDE_PATHS):
            return response

        duration_ms = 0
        if hasattr(request, '_audit_start_time'):
            duration_ms = int((time.time() - request._audit_start_time) * 1000)

        user = getattr(request, 'user', None)
        username = getattr(user, 'username', 'anonymous')
        user_id = getattr(user, 'id', None)

        logger.info(
            'API %s %s | user=%s (id=%s) | status=%s | %dms | ip=%s | ua=%s',
            request.method,
            path,
            username,
            user_id,
            response.status_code,
            duration_ms,
            self._get_client_ip(request),
            request.META.get('HTTP_USER_AGENT', '')[:120],
        )
        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
