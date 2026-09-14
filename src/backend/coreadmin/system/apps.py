from django.apps import AppConfig


class SystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'coreadmin.system'

    def ready(self):
        # 注册信号
        import coreadmin.system.signals  # 确保路径正确
