from django.apps import AppConfig


class CommercialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lims.commercial'
    label = 'commercial'
    verbose_name = '商务管理'
