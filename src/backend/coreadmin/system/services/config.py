from django.db import transaction
from coreadmin.system.models import SystemConfig


class ConfigService:
    @staticmethod
    def save_batch(rows):
        from coreadmin.system.views.system_config import SystemConfigCreateSerializer
        # Validate the entire proposed batch before writing anything.
        items = {row['id']: row for row in rows}
        def validate(objects):
            from rest_framework.exceptions import NotFound
            if set(objects) != set(items):
                raise NotFound()
            serializers = []
            for key, data in items.items():
                serializer = SystemConfigCreateSerializer(objects[key], data=data)
                serializer.is_valid(raise_exception=True)
                serializers.append(serializer)
            return serializers
        validate(SystemConfig.objects.in_bulk(items))
        with transaction.atomic():
            objects = {obj.pk: obj for obj in SystemConfig.objects.select_for_update().filter(pk__in=items).order_by('pk')}
            # Repeat against locked state; never write using stale instances.
            from rest_framework.exceptions import NotFound
            if set(objects) != set(items):
                raise NotFound()
            for serializer in validate(objects):
                serializer.save()
