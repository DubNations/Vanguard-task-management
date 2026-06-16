from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': '尖兵部队'})


urlpatterns = [
    path('api/v1/health', health_check, name='health-check'),
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/tasks/', include('apps.tasks.urls')),
    path('api/v1/files/', include('apps.files.urls')),
    path('api/v1/imports/', include('apps.imports.urls')),
    path('api/v1/exports/', include('apps.exports.urls')),
    path('api/v1/dashboard/', include('apps.dashboard.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/admin/', include('apps.admin_api.urls')),
    path('api/v1/points/', include('apps.points.urls')),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
