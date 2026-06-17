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
    """记录每个 API 请求到审计日志（文件 + 数据库）。"""

    EXCLUDE_PATHS = ['/api/v1/health', '/static/', '/__debug__/', '/nginx-health']

    METHOD_ACTION_MAP = {
        'POST': 'CREATE',
        'PUT': 'UPDATE',
        'PATCH': 'UPDATE',
        'DELETE': 'DELETE',
    }

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
        client_ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:120]

        logger.info(
            'API %s %s | user=%s (id=%s) | status=%s | %dms | ip=%s | ua=%s',
            request.method, path, username, user_id,
            response.status_code, duration_ms, client_ip, user_agent,
        )

        # Write to database (non-blocking, never break the request)
        try:
            if user and hasattr(user, 'pk') and user.pk:
                from apps.audit.models import AuditLog
                action = self.METHOD_ACTION_MAP.get(request.method, 'UPDATE')
                if '/login/' in path or '/token/' in path:
                    action = 'LOGIN'
                elif '/logout/' in path:
                    action = 'LOGOUT'

                # Extract resource type from path segments
                segments = [s for s in path.strip('/').split('/') if s and s not in ('api', 'v1')]
                resource_type = segments[0] if segments else 'unknown'
                resource_id = segments[1] if len(segments) > 1 and segments[1] != '' else ''

                AuditLog.objects.create(
                    user=user,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    description=f'{request.method} {path}',
                    detail={
                        'status_code': response.status_code,
                        'duration_ms': duration_ms,
                    },
                    ip_address=client_ip,
                    user_agent=user_agent,
                )
        except Exception:
            logger.debug('Audit log DB write failed', exc_info=True)

        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
