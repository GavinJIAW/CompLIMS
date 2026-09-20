from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lims.catalog'
    label = 'catalog'
    verbose_name = '服务目录'
