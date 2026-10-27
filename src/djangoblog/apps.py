# zhang: DjangoBlog 应用配置，负责在应用初始化完成后加载项目插件。
from django.apps import AppConfig

# zhang: 定义 djangoblog 应用的配置及启动时的初始化行为。
class DjangoblogAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'djangoblog'

    def ready(self):
        # zhang: 在 Django 应用注册表就绪后执行插件加载，保留父类初始化流程。
        super().ready()
        # Import and load plugins here
        # zhang: 延迟导入插件加载器，避免在应用初始化之前导入插件相关模块。
        from .plugin_manage.loader import load_plugins
        load_plugins()
