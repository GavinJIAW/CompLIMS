from django.apps import AppConfig


class CustomerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lims.customer'
    label = 'customer'
    verbose_name = '客户管理'
