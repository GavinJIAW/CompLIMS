import time

from django.db.models.signals import post_save, post_delete
from django.dispatch import Signal, receiver
from django.core.cache import cache
from coreadmin.system.models import MessageCenterTargetUser, SystemConfig, Dictionary
from coreadmin.system.services.effects import after_commit
from application import dispatch

# 初始化信号
pre_init_complete = Signal()
detail_init_complete = Signal()
post_init_complete = Signal()
# 租户初始化信号
pre_tenants_init_complete = Signal()
detail_tenants_init_complete = Signal()
post_tenants_init_complete = Signal()
post_tenants_all_init_complete = Signal()
# 租户创建完成信号
tenants_create_complete = Signal()

# 全局变量用于标记最后修改时间
last_db_change_time = time.time()


@receiver(post_save, sender=MessageCenterTargetUser)
@receiver(post_delete, sender=MessageCenterTargetUser)
def update_last_change_time(sender, **kwargs):
    after_commit(lambda: cache.set('last_db_change_time', time.time(), timeout=None))  # 设置永不超时的键值对


@receiver(post_delete, sender=SystemConfig)
def config_deleted(sender, **kwargs):
    after_commit(dispatch.refresh_system_config)


@receiver(post_delete, sender=Dictionary)
def dictionary_deleted(sender, **kwargs):
    after_commit(dispatch.refresh_dictionary)
