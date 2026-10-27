"""
WSGI config for djangoblog project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

# zhang: 导入环境变量处理模块，用于指定Django项目的配置入口。
import os

from django.core.wsgi import get_wsgi_application

# zhang: 未设置配置模块时，默认使用djangoblog.settings；保留已有环境变量配置。
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangoblog.settings")

# zhang: 创建WSGI应用对象，供兼容WSGI的服务器调用。
application = get_wsgi_application()
