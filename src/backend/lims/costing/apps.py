from django.apps import AppConfig


class CostingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lims.costing'
    label = 'costing'
    verbose_name = '成本管理'
