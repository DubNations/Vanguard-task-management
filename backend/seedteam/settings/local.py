"""
Windows 本地开发配置 — 通过 DJANGO_ENV=local 激活。

继承 dev.py 的所有配置，覆盖 Windows 不兼容项：
  - SQLite 替代 PostgreSQL（零配置）
  - WeasyPrint 标记为不可用（PDF 导出降级）
  - 日志简化为纯控制台
"""
from .dev import *  # noqa: F401,F403

# ------------------------------------------------------------------
# 1. 数据库：SQLite（零配置，单文件）
#    Django 5 的 JSONField 在 SQLite 上完全兼容
#    db.sqlite3 已在 .gitignore 中排除
# ------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
    }
}

# ------------------------------------------------------------------
# 2. WeasyPrint 不可用（GTK/Pango 原生库在 Windows 上难安装）
#    Excel / CSV 导出不受影响，PDF 导出将返回友好提示
# ------------------------------------------------------------------
WEASYPRINT_AVAILABLE = False

# ------------------------------------------------------------------
# 3. 日志简化为纯控制台输出
#    避免 Windows 文件锁和日志目录权限问题
# ------------------------------------------------------------------
for _logger_cfg in LOGGING['loggers'].values():  # noqa: F405
    _logger_cfg['handlers'] = ['console']
