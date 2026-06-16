from rest_framework.throttling import UserRateThrottle as _UserRateThrottle, AnonRateThrottle


class UserRateThrottle(_UserRateThrottle):
    """通用 API 限速：120次/分钟。"""
    scope = 'user'


class LoginRateThrottle(AnonRateThrottle):
    """登录接口限速：10次/分钟。"""
    scope = 'login'

    def get_cache_key(self, request, view):
        if request.path.endswith('/login/') or request.path.endswith('/token/'):
            return self.cache_format % {
                'scope': self.scope,
                'ident': self.get_ident(request),
            }
        return None
